---
title: The library catalog can't see a station's own build manifest
type: dream
owner: marshal
status: archived
                    # shipped same day: Epic 36 (Stories 36.1, 36.2) done in pyforge-marshal's
                    # tracked ledger; llms-full-check clean against the real repo (352/320,
                    # zero findings); a synthetic-fixture regression suite proves the new
                    # station-manifest scan path (tests/scripts/test_llms_full_check.py)
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `library-catalog-manifest-sync`).

# The library catalog can't see a station's own build manifest

## The Dream

`docs/reference/library-llms-full.md` and its detector (`scripts/llms_full_check.py`)
promise one thing: every dependency the factory actually runs on is documented, and
drift from `pixi.toml` is caught automatically (`regenerable-factory`'s two-layer loop,
applied to this surface). That promise has a hole. Every `pyforge-*` station carries a
**second** dependency manifest the detector never reads: its own
`src/shared/packages/pyforge-<station>/pixi.toml` `[package.run-dependencies]` table —
the one `pixi-build-python` actually builds the station's conda package from. Root
`pixi.toml` only needs to re-declare a station's run-dep when there's a separate reason
to (a shared floor, a test-tooling use); most of a station's real run-deps resolve
silently through the built package's own metadata and never touch root `pixi.toml` at
all. The catalog and its detector, both scoped to root `pixi.toml` only, are structurally
blind to that whole class of already-shipped, already-used library.

The Dream is a catalog and a detector that see **both** manifests, so "documented" keeps
meaning what it says.

## Why now — measured, not feared

Found 2026-09-12 during an operator-directed audit of the catalog's own scope (recorded
in [[pyforge-unifying-strategy]]'s Realization log, "Manifest-sync gap found"). Cross-
checking all ten stations' own `[package.run-dependencies]` against root `pixi.toml`'s
active-dependency set (`scripts/llms_full_check.py::manifest_deps()`) surfaced seven
libraries that are real, directly-imported, already-shipped station code — confirmed
importable live in each station's own pixi env today — yet never appear anywhere in root
`pixi.toml` and are undocumented in the catalog:

| Library | Import name | Used directly by |
|---|---|---|
| `packaging` | `packaging` | pyforge-marshal, pyforge-mason, pyforge-warden |
| `jsonschema` | `jsonschema` | pyforge-doctor, pyforge-marshal, pyforge-warden |
| `psutil` | `psutil` | pyforge-marshal |
| `attrs` | `attrs` | pyforge-atlas |
| `packageurl-python` | `packageurl` | pyforge-warden |
| `license-expression` | `license_expression` | pyforge-warden |

(`pydantic` is a related, already-partially-documented case — a direct run-dep of
pyforge-atlas and pyforge-scribe, but the catalog's existing note only credits it as
"present transitively via pydantic-ai/fastmcp/agno." Sharpen, don't re-add.)

This is the same station manifest `tests/meta/test_manifest_sync.py` already keeps in
sync with each station's own `pyproject.toml` — the precedent for treating it as a real,
authoritative source, not a build-tool implementation detail. Story 12.1
(`spec-12-1-full-pixi-wiring-distribution-and-repo-gate-compliance`, pyforge-marshal,
done) already wired one station member (Genesis/copier) into root `pixi.toml` +
`environment.yaml` + the catalog by hand, and its own `deferred:` block flagged
pre-existing catalog drift as a known follow-up — this Dream is that follow-up, generalized
into a standing detector fix instead of another one-off hand-wiring pass.

## What it looks like when real

- The seven libraries above are declared in root `pixi.toml` (`local-recipes` plus each
  owning station's own `[feature.pyforge-<station>.dependencies]` block) and documented
  in `docs/reference/library-llms-full.md`.
- `scripts/llms_full_check.py` parses every `src/shared/packages/pyforge-*/pixi.toml`
  `[package.run-dependencies]` table alongside root `pixi.toml`, merged into the same
  active-dependency set it already builds — so a station adding a real run-dep to its own
  manifest without mirroring or documenting it fails the check the same way an
  undocumented root `pixi.toml` dep does today.
- `pixi run -e local-recipes llms-full-check` exits 0 with the merged surface, not just
  root `pixi.toml`.
- Existing behavior is unchanged for everything the detector already covers: exit codes
  (0 clean / 1 drift / 2 missing input), the "commented-out deps are out of scope" rule,
  and ghost-entry / floor-drift detection all apply identically to the newly-scanned
  manifests.

## Constraints / Non-goals

- **Not a station library-adoption decision.** This Dream is strictly the bookkeeping gap
  — libraries already adopted and working, invisible to the truth surfaces. The aspirational
  "should station X bind library Y" questions in [[pyforge-unifying-strategy]]'s "Estate
  leverage — installed, bind now" table (including `filelock`'s marshal/scribe extension)
  are a separate, already-tracked, forward-looking question and stay out of scope here.
- **No new manifest, no new convention.** The nested `pixi.toml [package.run-dependencies]`
  tables already exist and are already the real source of a station's conda run-deps
  (`tests/meta/test_manifest_sync.py` already enforces their sync with `pyproject.toml`).
  This Dream only teaches the detector to read what already exists.
- **Detector contract stays stable.** `llms_full_check.py`'s exit-code contract and CLI
  (`pixi run -e local-recipes llms-full-check`) do not change shape; the fix widens what
  it reads, not how it is invoked or what its output means.

## Kinships

[[pyforge-unifying-strategy]] (owning Dream — the finding was made and recorded there;
this satellite carries the fix so the mega-spec doesn't absorb an unrelated tooling CAP)
· [[regenerable-factory]] (the two-layer detector/reconciler loop pattern this closes a
blind spot in) · [[pyforge-marshal]] (owner; Story 12.1's pixi-wiring precedent) ·
[[pyforge-atlas]] · [[pyforge-doctor]] · [[pyforge-mason]] · [[pyforge-warden]] (the four
stations whose undocumented run-deps this Dream closes).

## Realization log

- **2026-09-12** — Seeded (operator ruling: every effort enters through the Dream-to-Code
  chain, gap-closure included). Finding made and fully investigated in
  [[pyforge-unifying-strategy]]'s Realization log ("Manifest-sync gap found"); this
  satellite Dream carries the fix itself so it lands as a scoped `pyforge-marshal` story
  rather than a new CAP inside the Unifying mega-spec. Next act: `bmad-spec` derives
  `spec-library-catalog-manifest-sync` under `pyforge-marshal`.
- **2026-09-12 (spec + process correction)** — `bmad-spec` derived `spec-library-catalog-manifest-sync`
  (CAP-1, CAP-2; `status: ready`, zero open questions — every fact confirmed live before
  authoring). CAP-1/CAP-2 were then hand-implemented directly from the Spec with **no Story
  minted and no sprint-status ledger entry** — caught mid-turn by the operator. Reconciled
  same-turn: Epic 36 (Stories 36.1, 36.2) minted in `pyforge-marshal/epics.md`; `sprint_plan.py
  generate` + `sprint-ledger-sync` + `story-status-check` landed both `done` in the tracked
  ledger. `AGENTS.md` § Dream-first workflow gained item 5 and `CLAUDE.md`'s Dream-first
  paragraph gained a matching clause, both citing this incident, so a `ready` Spec is never
  again treated as license to skip decomposition.
- **2026-09-12 (realized)** — CAP-1 verified: seven libraries (the original six plus `filelock`,
  a CAP-1 scoping miss found and fixed the moment CAP-2's own scan went live — see Story 36.1's
  own note) mirrored into root `pixi.toml` and documented in the catalog; `llms-full-check`
  clean (352 active deps / 320 catalog entries) and `pixi lock --check` confirms every floor
  was already resolved, no new solve. CAP-2 verified: `scripts/llms_full_check.py` now scans
  every station's own nested `pixi.toml [package.run-dependencies]`, proven by a new
  `tests/scripts/test_llms_full_check.py` (5 tests, synthetic-fixture regression coverage) and
  a clean run against the real repo. Both Stories `done`; Dream `dreamt → realized`.
