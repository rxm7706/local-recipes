---
title: 'Downstream handoff to Mason — structured candidate handoff with a required health-screen verdict (S-13.5, FR-68/CAP-5)'
type: 'feature'
created: '2026-08-10'
status: done
baseline_revision: '24e89ba9d8c2d91108ca33a1ed20d4145ba90a1f'
final_revision: '34d1e280d12d2d16a08b2e6272c661af024d1926'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-13-context.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/SPEC.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md',
  '{project-root}/_bmad-output/implementation-artifacts/spec-13-4-fixed-source-audit-track.md',
]
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** CAP-1/2/3 can list tier-1/2 candidates but nothing turns ONE chosen candidate
into a structured, gated artifact for the packaging factory — CAP-5's own success signal
("a candidate reaching packaging carries a recorded health-screen verdict") is
unimplemented. Three deferred-work items were explicitly left for this story: multi-window
duplicate rows, no documented schema for a candidate envelope, and the
`unclassified-needs-human` reason's ambiguity under a not-on-cf filter.

**Approach:** A new read-only, single-candidate CLI (`trending-handoff`) looks up one
repo in the already-classified `trending_candidates_classified` dataset, requires a
caller-supplied health-screen verdict (abandonment signal + license clarity — pyforge-doctor's
existing watch axes are feedstock-scoped and cannot reach a pre-packaging repo with no
feedstock), and on a passing tier-1/2 candidate emits ONE schema-documented JSON record.
Any ineligible or under-specified input is refused, never silently passed.

## Boundaries & Constraints

**Always:**
- Every call resolves to either a structured JSON record (stdout, exit 0) or a refusal
  (stderr message, exit 1 or 2) — never a partial or ambiguous result.
- The health-screen gate runs on EVERY call — no `--force`/skip flag.
- Reuse the existing `_session`/`_provenance` read seam exactly as
  `trending_candidates/query.py` does — no new fetch, no new catalog entry, no new Kedro
  node (this mirrors CAP-3's own non-pipeline shape).
- NFR-6 exit codes: 0 pass, 1 policy-fail (`ValueError` — ineligible candidate, missing/failing
  health screen, dataset not yet ingested), 2 error (unexpected exception), 130 interrupted.
- Gate eligibility on the row's `tier` (`"1"`/`"2"`) directly, never on the `not_on_cf`
  boolean — resolves the `unclassified-needs-human` ambiguity by construction, since
  `_classify_row` only ever pairs tier `"1"`/`"2"` with a resolved OSI-license reason.
- A repo with duplicate rows across trending windows (daily/weekly/monthly) dedupes to
  exactly one handoff record, via the same deterministic sort `query.py` already uses
  (`stars_total` desc / `repo_full_name` asc / `period` asc).

**Block If:** Mason (`pyforge-mason`) already has a committed, documented intake
format/location for candidate handoff data. Verified live for this spec: `spec-packaging-factory/SPEC.md`
and `epics.md` in `_bmad-output/projects/pyforge-mason/planning-artifacts/` contain zero
references to "trending"/"candidate"/"campaign machinery"/"intake" — no such contract
exists today, so this does not currently block. If a future run finds one, HALT rather
than inventing a competing format.

**Never:**
- Compute or call pyforge-doctor's actual abandonment/license logic, or any live scan —
  SPEC.md's own CAP-5 non-goal. The verdict is a caller-supplied recorded input; this
  story builds the structural gate ("the gate exists"), not the screen itself.
- Validate the TRUTH of supplied health-screen evidence — only that both fields are
  present and non-empty. The operator/agent is trusted for accuracy (mirrors the
  org-audit list's git-review-decides trust model, spec-13-4 Design Notes).
- Auto-submit a recipe, open a staged-recipes PR, or author any recipe content.
- Add a `jsonschema` (or any new) pixi dependency — it is present only as an undeclared
  transitive today; disproportionate to an XS story (Simplicity First).
- Add or modify a Kedro pipeline node, catalog entry, or `NODE_TIMEOUTS` row.
- Touch `org_audit_candidates_classified` (CAP-4's dataset) — S-13.5 depends only on
  S-13.3 per `epic-13-context.md`'s dependency graph; wiring CAP-4's output into this or
  any query surface is a future CAP-3 extension (spec-13-4's own Auto Run Result note).
- Add an MCP tool — `mcp/audit.py`'s `CLI_ONLY_TOOLS` already precedents CLI-only atlas
  surfaces; a one-shot gate action has no query/browse use case an MCP client needs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Tier-1 repo in the classified set; `--verdict pass` + non-empty `--abandonment-signal`/`--license-clarity` | One JSON record on stdout: repo identity, tier/reason, `health_screen` block, provenance, `handed_off_at` epoch-seconds | exit 0 |
| Candidate not found | `--repo` not present in `trending_candidates_classified` | Refused | `ValueError` naming the repo; stderr; exit 1 |
| Tier = skip | Matching row has `tier="skip"` | Refused | `ValueError` naming tier + `reason`; stderr; exit 1 |
| Verdict = fail | `--verdict fail` | Refused (screen must PASS) | `ValueError`; stderr; exit 1 |
| Missing evidence field | `--abandonment-signal ""` or omitted | Refused | `ValueError` naming the missing field; stderr; exit 1 |
| Multi-window duplicate | Same repo appears with `period=daily` and `period=weekly` | Exactly one record, deterministically selected | No error |
| Case-insensitive repo match | `--repo Alice/LibFoo` vs stored `alice/libfoo` | Matches (casefold, mirrors CAP-4's dedup precedent) | No error |
| Dataset not yet ingested | `trending_candidates_classified` has no backing file | Refused | `ValueError`/`DatasetError`-derived message; stderr; exit 1 (indeterminate → 1, NFR-6) |
| Unexpected bootstrap failure | e.g. missing `conf/local/credentials.yml` | Not swallowed as policy-fail | Raw exception class + message to stderr; exit 2 |

</intent-contract>

## Code Map

- `src/pyforge/atlas/trending_candidates/handoff.py` -- NEW. `HANDOFF_SCHEMA_VERSION`,
  `HANDOFF_ENVELOPE_SCHEMA` (JSON-Schema-shaped dict), `_ELIGIBLE_TIERS`,
  `_select_candidate_row(df, repo_full_name)`, `hand_off_candidate(*, repo_full_name,
  verdict, abandonment_signal, license_clarity, project_path=None, env=None) -> dict`.
  Mirrors `query.py`'s read seam (`_session.bootstrapped_session` +
  `_provenance.load_with_provenance`) and its "validate first, raise `ValueError`"
  contract.
- `src/pyforge/atlas/trending_candidates/handoff_main.py` -- NEW CLI entrypoint
  (`python -m pyforge.atlas.trending_candidates.handoff_main`). Mirrors `__main__.py`'s
  deferred-import-after-`logging.disable`, BrokenPipeError, and broad-exception-to-stderr
  patterns, but output is unconditionally JSON (no table mode) and exceptions map to
  NFR-6 codes: `ValueError` -> 1, anything else -> 2.
- `pixi.toml` -- append `[feature.pyforge-atlas.tasks.trending-handoff]` near the existing
  `trending-candidates` task (~line 1502), same doc-comment style.
- `tests/trending_candidates/test_handoff.py` -- NEW. Reuses `conftest.py`'s
  `seed_catalog` fixture; one test per I/O matrix row plus a structural
  conformance check of the happy-path record against `HANDOFF_ENVELOPE_SCHEMA`.
- `_bmad-output/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md` --
  append an "As-built (Story 13.5, 2026-08-10)" note (mirrors 13.3's own), documenting
  the `trending-handoff` gate contract.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append resolution notes
  (never delete) to the 3 entries this story addresses: the multi-window dedup item
  (source_spec `spec-13-2-tier-classification.md`, "A repo trending in more than one
  window..."), the envelope-schema item (source_spec
  `spec-13-3-trending-candidates-operator-surface.md`, "no schema artifact... exists"),
  and the `unclassified-needs-human`/not-on-cf ambiguity item (same source_spec, "The
  default `--not-on-cf` filter excludes only...").

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/atlas/trending_candidates/handoff.py` -- implement `hand_off_candidate`
  per the I/O matrix: locate + dedup the row (casefold match on `repo_full_name`, sorted
  by `stars_total` desc / `repo_full_name` asc / `period` asc, take first), gate on
  `tier in {"1","2"}`, gate on `verdict == "pass"` and both evidence strings non-empty
  (after `.strip()`), assemble the record, mask NaN/±inf the same way `query.py` does for
  any numeric field carried through.
- [x] `src/pyforge/atlas/trending_candidates/handoff_main.py` -- argparse flags `--repo`
  (required), `--verdict {pass,fail}` (required), `--abandonment-signal TEXT` (required),
  `--license-clarity TEXT` (required); call `hand_off_candidate`; print
  `json.dumps(record)` on success.
- [x] `pixi.toml` -- add the `trending-handoff` task
  (`cmd = "python -m pyforge.atlas.trending_candidates.handoff_main"`).
- [x] `tests/trending_candidates/test_handoff.py` -- one test per I/O matrix row (9
  scenarios) + the schema-conformance test.
- [x] `tier-taxonomy.md` -- add the as-built note (CLI name, flags, gate contract, the
  tier-based eligibility resolution of the not-on-cf ambiguity).
- [x] `deferred-work.md` -- append the 3 resolution notes described in Code Map.

**Acceptance Criteria:**
- Given a tier-1 or tier-2 candidate in `trending_candidates_classified` and a passing
  health screen with both evidence fields populated, when `trending-handoff` runs, then
  it prints one structured JSON record to stdout and exits 0 — never a recipe, never a PR
  (FR-68 / CAP-5's literal AC).
- Given a `tier="skip"` candidate, a `--verdict fail`, or a missing evidence field, when
  `trending-handoff` runs, then it refuses (no JSON emitted, exit 1) with a stderr
  message naming the specific reason — discovery output alone never opens a
  staged-recipes PR (SPEC.md CAP-5 success signal).
- Given `pixi run --frozen -e pyforge-atlas pytest tests/trending_candidates/test_handoff.py -q`,
  when run, then it passes.
- Given `pixi run --frozen -e pyforge-atlas kedro-test`, when run after this change, then
  it still passes (no pipeline/catalog change; import-smoke covers the new modules).
- Given `python3 scripts/spec_surface_check.py`, when run after this change, then it
  reports `OK` (scoped `.memlog.md` reconcile + baseline re-stamp).

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 1: (low 1)
- reject: 4: (low 4)
- addressed_findings:
  - `medium` `patch` `_select_candidate_row`'s multi-window dedup sort ordered the
    raw, uncoerced `stars_total` column — a numeric-looking STRING cell (a real
    scraped-data shape `query.py` already had to fix, "verified live" per its own
    docstring) could raise a `TypeError` or silently mis-order the tie-break when it
    met a genuine `int` on another duplicate-window row for the same repo. Fixed:
    the sort order is now computed from a separate `pd.to_numeric(...,
    errors="coerce")`-coerced frame; the returned row's own `stars_total` value is
    untouched. Pinned by a new test with mixed `str`/`int` `stars_total` values
    across duplicate windows.
  - `low` `patch` The dedup match stripped the CALLER's `--repo` argument before
    casefold-comparing but not the STORED `repo_full_name` value, so a scraped row
    with incidental leading/trailing whitespace would silently fail to match an
    otherwise byte-correct `--repo` argument. Fixed: both sides are now stripped.
    Pinned by a new test with a whitespace-padded stored value.
  - `low` `patch` The envelope assembly blind-overwrote `dataset`/`health_screen`/
    `provenance`/`handed_off_at`/`schema_version` on the selected row with no
    collision guard — a future CAP-2 column sharing one of those exact names would
    vanish into this envelope's own bookkeeping with no error. Fixed: added
    `_RESERVED_ENVELOPE_KEYS` and a pre-overwrite collision check that raises
    `ValueError` naming the colliding key(s). Pinned by a new test.
  - `low` `patch` `HANDOFF_ENVELOPE_SCHEMA["required"]` omitted `dataset`/
    `provenance`/`handed_off_at` even though `hand_off_candidate` sets all three
    unconditionally on every successful record — the schema under-promised what the
    code always delivers. Fixed: added all three to `required`.
  - `low` `patch` The hand-rolled schema-conformance test walker (`_assert_conforms`)
    checked `type`/`enum`/`const` but not the schema's own `minLength` constraint on
    the health-screen evidence fields, so the schema and its own "conformance" test
    could drift apart on that constraint with no test catching it. Fixed: added a
    `minLength` clause to the walker.
  - `low` `patch` `trending_candidates/__init__.py`'s module docstring still
    described the package as CAP-3-only, with no mention that it now also hosts
    CAP-5's `handoff`/`handoff_main` modules. Fixed: updated the docstring.
  - `low` `patch` `handoff_main.py`'s `except ValueError`/`except Exception` stderr
    `print` calls were unguarded against `BrokenPipeError`, unlike the guarded
    stdout success path — a broken stderr pipe while reporting an error would raise
    `BrokenPipeError` from INSIDE the except block itself, escaping `main()` as a
    raw traceback instead of the documented clean exit code (the sibling `except
    BrokenPipeError:` clause only catches one raised from the `try` body, never one
    raised from another `except` block). Fixed: both prints wrapped in
    `contextlib.suppress(BrokenPipeError)`. Pinned by a new test mirroring
    `test_main.py`'s `_ClosedPipe` model, applied to stderr instead of stdout.
  - deferred (1, ledger): the two CLI entrypoints now living in
    `trending_candidates/` (`__main__.py` from Story 13.3, `handoff_main.py` from
    this story) enforce incompatible exit-code contracts for the same failure
    classes — `__main__.py` maps every failure to exit 1 uniformly, while
    `handoff_main.py` implements NFR-6's full 0/1/2/130 scheme and maps
    `BrokenPipeError` to 2 where `__main__.py` maps it to 1. `handoff_main.py` is
    the more NFR-6-correct of the two; fixing `__main__.py` to match is out of this
    story's scope (Never list: no touches to `query.py`/`__main__.py`'s own
    semantics) and belongs to a future story or a `__main__.py`-focused patch.
  - rejected (4, noise): a claim that no `spec-13-5-*.md` file exists anywhere in
    the repo (false — this very file, `spec-13-5-downstream-handoff-to-mason.md`,
    has existed since before implementation began; the reviewer's search evidently
    missed it, mirroring a near-identical false "spec file doesn't exist" claim
    already rejected on story 13.4's own review pass); a style objection to
    `handoff.py` importing the underscore-prefixed `_INF`/`_narrow_integral_floats`
    directly from `query.py` (a deliberate, already-reasoned trade-off — Design
    Notes: reuse rather than duplicate the NaN/±inf masking logic, since an
    independent copy would silently drift the moment either changed, and this
    story's Code Map explicitly does not touch `query.py` itself, Surgical
    Changes); a claim that
    `test_happy_path_emits_one_record_never_a_recipe_or_pr`'s `assert "recipe" not
    in record` / `assert "pr_url" not in record` are "tautological" (true but
    inconsequential — a harmless documentation-style assertion pinning SPEC.md's
    own "never a recipe, never a PR" language, not a defect); a claim that the
    dedup step picks a duplicate-window row by `stars_total`/`period` BEFORE
    checking tier, so window-duplicate rows with DIFFERENT tiers could cause a
    false refusal — verified false by re-reading `_classify_row`
    (`pipelines/upstream_discovery/nodes.py`): tier is resolved solely from
    `repo_full_name` (via `pypi_name`/`on_cf`/`intel`, none of which read `period`
    or `stars_total`), and `trending_candidates_classified` is a plain
    `ParquetDataset` fully overwritten by ONE classify run each ingest (confirmed
    via `query.py`'s own docstring, "a plain `ParquetDataset`") — so every
    duplicate-window row for the same repo is classified from the SAME join-table
    snapshot and is GUARANTEED to carry the identical tier/reason; the premise
    describes a state the shipped classifier cannot produce.

### 2026-08-10 — Repair pass (deterministic verification failure)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 2: (low 2)
- reject: 4: (low 4)
- addressed_findings:
  - The prior session's implementation and review (above) had already landed and
    committed cleanly, but `python3 scripts/spec_surface_check.py` failed: the
    3 new files (`handoff.py`, `handoff_main.py`, `test_handoff.py`) were already
    named in `spec-pyforge-atlas`'s `.memlog.md`, yet
    `scripts/.spec-surface-baseline.json` never captured their hashes — the
    prior session's `--write-baseline --spec pyforge-atlas/spec-pyforge-atlas`
    ran before the 3 files were tracked in git, so the stamp silently omitted
    them. Fixed by re-running that exact command now that the files are tracked
    (no code or spec-content change; `scripts/.spec-surface-baseline.json` gains
    3 hash entries, 3 lines). Blind Hunter + Edge Case Hunter reviewed this
    repair's diff (the baseline JSON only, since the code itself was already
    reviewed and unchanged in this pass): both independently flagged that
    `spec_surface_check.py --write-baseline` has no structural safeguard against
    this exact staleness class recurring (working-tree-byte hashing instead of
    the committed git blob, no completeness/memlog cross-check, no lock against
    concurrent writers) — real gaps in the detector tool itself, pre-existing
    and out of this story's scope (the frozen intent contract governs the
    `trending-handoff` CLI, not `spec_surface_check.py`), so both deferred to
    `deferred-work.md` (2 entries: missing staleness safeguards; unlocked
    concurrent-write race). Four other claims (baseline write may have silently
    absorbed unrelated drift; another spec's baseline may be left stale; the
    diff can't self-certify surface health; hash values aren't casually
    reviewable) were checked directly against the tool's own output — a full
    unscoped `spec_surface_check.py` run showed exactly 3 findings (only the 3
    target files) before this fix and 0 findings across all 54 specs after —
    and rejected as verified false or inherent-to-format noise. Re-verified
    live: `pytest src/shared/packages/pyforge-atlas/tests/trending_candidates -q`
    73 passed, `kedro-test` 1073 passed / 19 skipped, `python3
    scripts/spec_surface_check.py` reports `OK: every tracked file governed or
    allowlisted; no drift.` (exit 0).

## Design Notes

**Why the health-screen verdict is caller-supplied, not computed.** pyforge-doctor's
abandonment axis composes `feedstock_health` (filtered `stuck`/`bad`) + `release_cadence`
— both keyed to an ALREADY-tracked conda-forge feedstock (doctor `epics.md` Story 2.2).
A discovery candidate is by definition not-yet-on-conda-forge (CAP-3's default
`--not-on-cf` filter), so no feedstock exists for doctor to diagnose; Story 13.2's own
Design Notes independently confirm `vcs_health` "only enriches FROM an already-known
feedstock's repo, the opposite direction." SPEC.md's CAP-5 non-goal states building the
screen logic is pyforge-doctor's job, not this kernel's — so this story builds the
structural requirement ("the gate exists") and takes the verdict as input. A future story
can wire an automated screen behind the same two parameters with zero CLI contract
change.

**Why tier gates eligibility instead of `not_on_cf`.** `_classify_row` (nodes.py) only
ever returns tier `"1"`/`"2"` together with a resolved OSI-license reason string;
`"already-on-conda-forge"` and `"unclassified-needs-human"` are ALWAYS tier `"skip"`.
Gating on `tier in {"1","2"}` therefore excludes both automatically, without touching
`query_trending_candidates`'s own filter semantics — which deferred-work explicitly says
not to patch as a "contract amendment."

**Why a Python dict schema, not a `.schema.json` file + the `jsonschema` library.** No
data file lives inside `src/pyforge/atlas/` today (config lives under `conf/`); `jsonschema`
resolves only as an undeclared transitive (confirmed via `pixi list -e pyforge-atlas`),
and declaring it explicitly triggers this repo's pixi.toml/environment.yaml PR gate for
an XS story. `HANDOFF_ENVELOPE_SCHEMA` is authored in real JSON-Schema-draft-2020-12
vocabulary (`type`/`properties`/`required`) as a plain dict — genuinely "a documented
schema," dumpable via `json.dumps` for an external consumer — and the test performs a
hand-rolled structural walk (required keys present, primitive types match) rather than
depending on the `jsonschema` package:

```python
HANDOFF_ENVELOPE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "repo_full_name", "tier", "health_screen"],
    "properties": {
        "schema_version": {"type": "integer"},
        "repo_full_name": {"type": "string"},
        "tier": {"enum": ["1", "2"]},
        "health_screen": {"type": "object",
            "required": ["verdict", "abandonment_signal", "license_clarity"]},
    },
}
```

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Story 13.5 (CAP-5, FR-68) implementation and review landed cleanly in
the prior session — `hand_off_candidate` + the `trending-handoff` CLI, gated on
tier + a caller-supplied passing health screen, emitting one schema-documented
JSON record and never a recipe or PR. Deterministic verification then failed on
`python3 scripts/spec_surface_check.py`: the drift baseline was stamped before
the 3 new files were tracked in git, so it never captured their hashes despite
the memlog already naming them. This repair pass re-ran the exact reconciliation
command the spec's own Verification section prescribes
(`--write-baseline --spec pyforge-atlas/spec-pyforge-atlas`); no source code or
`<intent-contract>` content changed.

**Files changed (this repair pass):**
- `scripts/.spec-surface-baseline.json` -- 3 lines added: SHA1 hashes for
  `handoff.py`, `handoff_main.py`, `test_handoff.py` under
  `pyforge-atlas/spec-pyforge-atlas`'s tracked-file baseline.
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/deferred-work.md`
  -- 2 new defer entries (detector-tooling robustness gaps surfaced by this
  pass's review, out of this story's scope).
- `spec-13-5-downstream-handoff-to-mason.md` -- this repair pass's triage log
  entry + this result section.

**Review findings breakdown (this repair pass):** 0 patch (the diff itself —
a baseline hash stamp — was verified byte-correct by independent SHA1
recomputation), 2 defer (low; pre-existing `spec_surface_check.py` staleness/
concurrency safeguard gaps), 4 reject (low; claims checked directly against
the tool's own before/after output and found false, or inherent-to-format
noise).

**Verification performed:**
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/trending_candidates -q` -- 73 passed.
- `pixi run --frozen -e pyforge-atlas kedro-test` -- 1073 passed, 19 skipped.
- `python3 scripts/spec_surface_check.py` -- `OK: every tracked file governed or allowlisted; no drift.` exit 0.
- `python3 scripts/spec_surface_check.py --json` -- `findings: []`.

**Residual risks:** None from this story's own contract — it is fully
implemented, tested, and verified green. The 2 deferred findings are about
`spec_surface_check.py` itself (a detector this story does not own or touch)
and do not block or affect story 13.5's shipped behavior.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `12-5-downstream-handoff-to-mason-fr-68: done`).
