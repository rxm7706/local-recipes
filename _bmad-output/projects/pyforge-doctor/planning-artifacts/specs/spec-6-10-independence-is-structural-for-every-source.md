---
title: "Story 6-10: Independence is structural, for every source"
type: "feature"
created: "2026-08-09"
status: "done"
authored: "spec-first, ahead of implementation (operator instruction 2026-08-09: seed -> Dream -> Spec -> code)"
owner-dream: docs/dreams/pyforge-doctor.md
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py'
  - '{project-root}/src/shared/packages/pyforge-doctor/tests/unit/test_sources_deps_independence.py'
---

## Intent

Replace six near-identical per-source independence tests with **one meta-test driven by the
registry**, so that independence is a property of *every* source — including sources not yet
written — rather than a habit each story remembers to repeat. FR-15; AD-11, AD-12.

**Surface:** `tests/meta/test_source_independence.py`

## Acceptance Criteria

- **Given** every Doctor source declares the station it judges, **When** the meta-test runs,
  **Then** no source imports the package of the station it judges — **including lazy imports
  and string constants that could reach `import_module`**.
- **And** `sources/warden.py` is an **explicitly allowlisted exception with its reason
  recorded** (it relays an instrument's self-report about its own environment, which is not
  judging an artifact).
- **And** a newly added source **with no declared subject fails the test**.

## Design notes

### The registry is what makes this possible

`sources/__init__.py`'s `REGISTRY` (Story 6.2) already carries `subject_station` per source
and **fails loud at construction** on a missing one. `test_sources_registry.py` pins
`REGISTRY` and `Source` in exact set-equality both directions. So the meta-test does not need
its own source list — it derives one, and a new `Source` member cannot escape it. That is the
difference between this story and the six tests it replaces: those are per-file and a
seventh source simply wouldn't be covered.

The third AC — *a source with no declared subject fails* — is largely already delivered by
`SourceRegistration.__post_init__`. The meta-test should still assert it, but by construction
rather than duplication: prove a registration missing `subject_station` raises, and that the
meta-test's own module→source mapping has **no unmapped source and no unmapped module**, so
a source whose file cannot be located is a failure rather than a silent skip.

### Two exceptions, not one — and only one of them is `warden`

The AC names `sources/warden.py`. Implementation must also carry **AD-13** from Story 6.7,
which is a different shape and must not be folded into the same allowlist entry:

| module | what it may import | why |
|---|---|---|
| `sources/warden.py` | `pyforge.warden` | relays an instrument's **self-report about its own environment** — not judging an artifact (AD-11's stated exception) |
| `sources/deps.py` | **nothing extra** | it is *stricter* than the rule: it bars `bmad_loop` (the harness) as well as `pyforge.marshal`, per AD-13 |

`deps.py` is not an exception at all — it is the tightest source in the package. The
meta-test must not weaken it to the common rule. Either the generalised assertion is
"no station package **and** no judged machinery", or `deps.py` keeps its stricter local test
alongside. **Preferred:** generalise the rule to include harness packages, so 6.7's stricter
guarantee becomes the fleet default rather than a local accident.

### What to do with the six existing tests

`test_sources_marshal_independence.py`, `test_sources_ledger_independence.py`,
`test_sources_board_independence.py`, `test_sources_chain_independence.py`,
`test_sources_deps_independence.py` (+ warden's `test_no_warden_import.py`) all encode the
same AST walk. Deleting them wholesale trades six real assertions for one unproven one.

**Sequence:** land the meta-test first, confirm it fails when each per-file test would have
failed (mutation-test it once per source by inserting a forbidden import), *then* remove the
redundant per-file tests in a second commit. `deps.py`'s stricter test is the exception —
keep it unless the generalised rule provably subsumes it.

### The AST walk to inherit, not re-derive

The existing tests already handle the cases a naive version misses, and the meta-test should
lift their walk rather than rewrite it:

- imports **inside function bodies** (lazy is exactly how warden's legitimate import works)
- `node.level` relative imports skipped (`..models` is never a station)
- **string constants** checked separately, with **docstrings stripped first** — every one of
  these modules names the forbidden package repeatedly while explaining why it must not
  import it, so a naive string scan fails on the documentation

That docstring-stripping detail is load-bearing and easy to lose in a rewrite.

### Ordering

`Deps: S-6.9`. Sequenced last so it runs against the final set of sources, after the shims
retire. Nothing about the meta-test depends on the retirement, so if 6.9 stalls on its
blocking precondition (CI detector coverage), this story can land first without harm — the
dependency is tidiness, not correctness.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `6-10-independence-is-structural-for-every-source: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `6-10-independence-is-structural-for-every-source: done`).
- `## Auto Run Result` reconstructed from git (none survived).
