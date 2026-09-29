---
title: 'Fixed-source audit track — reuse the CAP-2 classifier against a declared candidate list (S-13.4, FR-67/CAP-4)'
type: 'feature'
created: '2026-08-10'
status: done
baseline_revision: '7680ca54a6d3df3daa30c3293beb86819120f946'
final_revision: 'a4919b1a13a3d0893a31f52ed0fedcce96299849'
review_loop_iteration: 0
followup_review_recommended: false # confirmed after review — 1 medium + 2 low patches, all localized to one new function + its tests; not significant enough to warrant an independent follow-up pass
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-13-context.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/SPEC.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/org-audit-precedent.md',
]
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 13.2's classifier only ever sees the moving trending feed (13.1), so a
fixed, hand-declared candidate source (a named org, a curated list) still requires a manual
`lookup_feedstock` sweep — exactly the June-2026 Microsoft org audit did by hand — with no
automated re-verification against current atlas state (FR-67, CAP-4).

**Approach:** Add two more nodes to the same `pipelines/upstream_discovery/` package: a pure
`load_org_audit_candidates` loader that turns a git-tracked, hand-curated `parameters.yml`
list into a DataFrame, and a second binding of the EXISTING, UNCHANGED
`classify_trending_candidates` function (Kedro's positional `inputs=[...]` list lets one
function serve two differently-named datasets) against that DataFrame instead of
`trending_candidates` — producing `org_audit_candidates_classified` with the identical
tiered/reasoned shape.

## Boundaries & Constraints

**Always:**
- `load_org_audit_candidates` is a PURE `params -> pd.DataFrame` node — no HTTP/parse
  import; the source is git-tracked config, not a live fetch, so there is no dataset-owned
  IO seam to inject (unlike CAP-1's scrape).
- `classify_org_audit_candidates` reuses `classify_trending_candidates` **unchanged** — same
  function, same decision tree, same helpers — bound via Kedro's positional `inputs=[...]`
  to `org_audit_candidates` instead of `trending_candidates`. Zero duplicated classification
  logic (CAP-4's literal intent: reuse CAP-2's classifier, not a one-off manual audit).
- A declared-list entry missing `repo_full_name`, a non-dict entry, or a non-string
  `repo_full_name` is excluded from the built DataFrame — never raises.
- A `None`/non-list `org_audit_candidates` parameter degrades to an empty DataFrame with the
  `repo_full_name` column; `classify_org_audit_candidates` then takes its own existing
  empty-input guard, producing an empty `org_audit_candidates_classified` with the full
  output schema — never an exception.
- `org_audit_candidates`/`org_audit_candidates_classified` gain the `org_audit` catalog
  domain prefix (added to `PREFIX_TO_PIPELINE` alongside the existing `trending` prefix, both
  resolving to `upstream_discovery` — mirrors the existing `seed`/`seed_gaps`
  two-prefix-one-pipeline precedent) so `kedro-catalog-check`'s naming gate recognizes them.
- Both new nodes get their own `NODE_TIMEOUTS` entry; no new `SCHEDULED_JOBS` row —
  `bootstrap_ops` is computed from the full node set (`node_ops - PHASE_P_OPS`), so both ride
  the existing weekly `bootstrap_data` job automatically, exactly as `classify_trending_candidates`
  already does.

**Block If:** None — reuses CAP-2's already-resolved classifier; the one new decision (where
the declared list lives) is closed below via a documented engineering default, consistent
with CAP-1/CAP-2's own "no further human input required" precedent.

**Never:**
- No new CLI/MCP operator surface for org-audit output — querying it is a future extension
  (13.5 Mason handoff, or a later CAP-3 generalization), out of scope here; 13.4 does not
  depend on 13.3.
- No live GitHub fetch or org-repo enumeration — CAP-1's HTML-scrape/Search-API
  infrastructure is untouched and unused (13.4 does not depend on 13.1, per the epic's own
  Cross-Story Dependencies).
- No change to `classify_trending_candidates`'s signature, decision tree, helpers, or the
  existing `trending_candidates`/`trending_candidates_classified` pipeline path.
- No merge/dedup between `org_audit_candidates_classified` and `trending_candidates_classified`
  — two independent datasets; the same repo appearing in both is not an error.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, live gap | Declared list has one repo resolving to a pure-python, OSI-licensed, not-yet-on-cf PyPI package | Row carries `tier="1"` in `org_audit_candidates_classified` | No error |
| Shipped independently since the list was written | Declared list has one repo whose resolved PyPI name is NOW present in `pypi_conda_mapping` | `tier="skip"`, `reason="already-on-conda-forge"` — dropped, not re-proposed (FR-67's literal contract) | No error |
| Empty/unset declared list | `org_audit_candidates` param is `[]` | `org_audit_candidates_classified` is an empty frame with the full output schema | No error, no exception |
| Malformed entry | A declared-list entry missing `repo_full_name`, a non-dict entry, or a non-string `repo_full_name` | That entry excluded from the built DataFrame; the rest classify normally | No error |
| `None`/non-list parameter | `org_audit_candidates` overridden to `null` or a non-list value | Degrades to an empty DataFrame with the `repo_full_name` schema | No error, no exception |

</intent-contract>

## Code Map

- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- add `load_org_audit_candidates(org_audit_candidates: list | None) -> pd.DataFrame`; `classify_trending_candidates` (already there, Story 13.2) is reused unchanged as CAP-4's classify half.
- `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` -- append two `node(...)` entries to the existing `Pipeline([...])` list (currently 2 nodes, lines 19-40).
- `conf/base/parameters.yml` -- add `org_audit_candidates:` (git-tracked, hand-curated `{repo_full_name}` list; the `ttls:` block at lines 18+ is the sibling declared-config precedent to mirror in comment style).
- `conf/base/catalog.yml` -- append two entries after the `upstream_discovery` banner block (lines ~810-854); update the header's and block's CAP-4-pending comments (lines ~39-40, ~824) to record CAP-4 landed.
- `tests/catalog/conftest.py` -- `PREFIX_TO_PIPELINE` (line 62) gains `"org_audit": "upstream_discovery"`; `EXPECTED_PIPELINE_COUNTS["upstream_discovery"]` (line 86) `2 -> 4`; `EXPECTED_TOTAL` (line 88) `88 -> 90`.
- `src/pyforge/atlas/orchestration/definitions.py` -- `NODE_TIMEOUTS` dict, `upstream_discovery` section (lines 260-262): add `load_org_audit_candidates` and `classify_org_audit_candidates` entries.
- `tests/pipelines/upstream_discovery/test_nodes.py` -- existing classifier test file (471 lines); extend with `load_org_audit_candidates` tests + a reuse/drop test.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- implement `load_org_audit_candidates(org_audit_candidates: list | None) -> pd.DataFrame`: build a `repo_full_name`-column frame from the declared list, skipping any entry missing/mistyping `repo_full_name` or a non-dict entry; `None`/non-list input (or an all-invalid list) degrades to an empty frame with the `repo_full_name` column -- CAP-4's ingest half (FR-67), pure params-in shape (no `RefreshRequest`/cadence machinery — there is no fetch to cadence-gate).
- [x] `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` -- append `node(func=load_org_audit_candidates, inputs="params:org_audit_candidates", outputs="org_audit_candidates", name="load_org_audit_candidates")` and `node(func=classify_trending_candidates, inputs=["org_audit_candidates", "pypi_universe", "pypi_conda_mapping", "pypi_intelligence_enriched"], outputs="org_audit_candidates_classified", name="classify_org_audit_candidates")` -- wires CAP-4's two nodes, reusing CAP-2's classifier unchanged.
- [x] `conf/base/parameters.yml` -- add `org_audit_candidates:`, a git-tracked list of `{repo_full_name: "org/repo"}` entries seeded with `org-audit-precedent.md`'s June-2026 Microsoft "material gaps" candidates (`microsoft/edit`, `microsoft/agent-framework`, `microsoft/qlib`, `microsoft/PyRIT`, `microsoft/promptflow`, `microsoft/semantic-kernel`, `microsoft/torchscale`, `microsoft/SEAL`, `microsoft/DiskANN`); a comment states the list is config-only, re-verified fresh every run against current atlas signals, and is NOT committed current scope (SPEC.md's own non-goal) -- the declared org-audit list FR-67 names.
- [x] `conf/base/catalog.yml` -- append `org_audit_candidates` (`type: pandas.ParquetDataset`, `filepath: data/raw/org_audit_candidates/org_audit_candidates.parquet`, `metadata.layer: raw`) and `org_audit_candidates_classified` (`type: pandas.ParquetDataset`, `filepath: data/derived/org_audit_candidates_classified/org_audit_candidates_classified.parquet`, `metadata.layer: derived`); update the two CAP-4-pending narration comments to record CAP-4 landed.
- [x] `tests/catalog/conftest.py` -- add `"org_audit": "upstream_discovery"` to `PREFIX_TO_PIPELINE`; bump `EXPECTED_PIPELINE_COUNTS["upstream_discovery"]` `2 -> 4` and `EXPECTED_TOTAL` `88 -> 90`.
- [x] `src/pyforge/atlas/orchestration/definitions.py` -- add `"load_org_audit_candidates": 30,  # CAP-4 (pure in-memory params->DataFrame, no network)` and `"classify_org_audit_candidates": 120,  # CAP-4 (reuses CAP-2's classifier, no network)` to `NODE_TIMEOUTS`.
- [x] `tests/pipelines/upstream_discovery/test_nodes.py` -- one test per I/O matrix row above for `load_org_audit_candidates` (happy path, malformed entry, empty list, `None`/non-list input), plus a reuse test proving `classify_trending_candidates` run against an `org_audit_candidates`-shaped frame reproduces the shipped-since-drop behavior (a repo resolving to a PyPI name present in `pypi_conda_mapping` classifies to `tier="skip"`/`reason="already-on-conda-forge"`) -- pins CAP-4's FR-67 contract.

**Acceptance Criteria:**
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this change, then it passes (the two new entries carry the `org_audit` domain prefix, a valid layer tag, and a conforming `data/<layer>/<name>/` filepath).
- Given `pixi run -e pyforge-atlas dagster-dryrun`, when run after this change, then it passes (`load_org_audit_candidates`/`classify_org_audit_candidates` each carry a `NODE_TIMEOUTS` entry; both ride the existing weekly `bootstrap_data` job with no new `SCHEDULED_JOBS` row).
- Given the declared `org_audit_candidates` list and current `pypi_universe`/`pypi_conda_mapping`/`pypi_intelligence_enriched` state, when `classify_org_audit_candidates` runs, then every declared candidate resolves to a tier or an enumerated `skip_reason` — never a silent drop — and one already present in `pypi_conda_mapping` classifies to `tier="skip"`/`reason="already-on-conda-forge"` (FR-67: a candidate that shipped independently since the list was written is dropped, not re-proposed).
- Given `pixi run -e pyforge-atlas kedro-test`, when run after this change, then it passes (new tests included; no HTTP/parse import lands in `nodes.py`).

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 2: (medium 2)
- reject: 7: (low 7)
- addressed_findings:
  - `medium` `patch` `load_org_audit_candidates` silently dropped a malformed list entry
    (non-dict entry, missing `repo_full_name`, or a non-string value) before it ever
    reached the classifier — inconsistent with `classify_trending_candidates`'s own
    stated invariant ("assigns a tier + reason to EVERY row — never a silent drop") and
    with this epic's pervasive never-silently-drop ethos. A hand-edit typo in
    `parameters.yml` (e.g. `repo_fullname:`) would vanish a candidate with zero signal.
    Fixed: every list entry now produces exactly one row (best-effort `repo_full_name`,
    `None` when unextractable), so a malformed entry reaches
    `classify_trending_candidates`'s already-robust `None`-handling path and surfaces as
    a visible `skip`/`no-pypi-artifact` (or `unclassified-needs-human`) row instead of
    disappearing.
  - `low` `patch` No dedup of `repo_full_name` entries — a literal or case-variant
    duplicate (`microsoft/edit` vs `Microsoft/Edit`) in the hand-curated list would flow
    through as duplicate output rows. Fixed: case-insensitive dedup (`casefold()`),
    keeping the first occurrence's original casing.
  - `low` `patch` The memlog's landing entry mistranscribed the seeded candidate list,
    dropping the `microsoft/` prefix from 8 of the 9 entries in its own prose summary
    (`parameters.yml` itself was always correct — a documentation-only defect). Fixed:
    corrected the memlog line to match the actual seeded data.
  - deferred (2, ledger): the reused `classify_trending_candidates` classifier can only
    ever reach a tier via a resolved PyPI name, so a genuinely PyPI-less candidate (e.g.
    a pure Rust/Go CLI or a C++ library with no Python bindings — two of the nine seeded
    org-audit candidates, `microsoft/edit` and `microsoft/SEAL`, are plausibly this
    shape) can never reach the Tier-2 outcome `tier-taxonomy.md`'s own definition allows
    for "Rust/Go CLI, native/compiled" candidates — a pre-existing structural gap in the
    Story 13.2 classifier, not introduced by this story, now newly consequential because
    CAP-4 feeds it exactly the kind of fixed-source batch (a real org audit) where such
    candidates are common. And the exact-normalized-repo-segment PyPI-name resolution
    heuristic (Story 13.2, already an accepted v1 limitation) false-negatives whenever a
    repo's PyPI package name differs from its own repo name — `org-audit-precedent.md`'s
    own data demonstrates this directly (`agent-framework-core` shipped separately from
    the `microsoft/agent-framework` repo at audit time); both are classifier-seam
    limitations for a future story to address, not a defect in this diff.
  - rejected (7, noise): committing the declared list to git-tracked `parameters.yml`
    "violates" SPEC.md's non-goal on treating it as committed scope (the non-goal warns
    against trusting the list's OLD classification, not against reusing its repo names
    as seed input — every run re-verifies fresh via the unchanged classifier, which is
    the literal mechanism FR-67 describes; already reasoned through in this spec's
    Design Notes); `org-audit-precedent.md`'s `lookup_feedstock`-before-commit
    instruction wasn't followed by hand (the classifier's automated re-verification on
    every run is a stronger, continuous form of the same instruction — the list of
    names alone carries no live-scope claim, only the classified OUTPUT does); CAP-4
    "reinvents" the `seed_lts_registry`-style direct-YAML-catalog-entry pattern instead
    of a params->node->parquet chain (a `yaml.YAMLDataset` still can't hand Kedro a
    `pd.DataFrame` directly — some node would be needed regardless, and this spec's
    Design Notes already reasoned through and rejected the `seed_root` precedent as a
    cross-project-reuse pattern that doesn't apply here); `org_audit_candidates_classified`
    has no read-side consumer yet (explicitly, deliberately scoped out in this spec's
    Never section — the identical incremental-delivery shape `trending_candidates_classified`
    itself had for one full story before CAP-3 landed a day later); landing CAP-4 before
    CAP-5 "doubles ungated exposure" (CAP-4 only produces a discovery dataset, never a
    packaging trigger — SPEC.md's own Constraints already forbid auto-submission, and
    the epic's own story order already established "classified output before the CAP-5
    gate" as the accepted sequence via `trending_candidates_classified`); the new
    node/test docstrings cite a spec file "that does not exist" (false — verified live,
    `_bmad-output/implementation-artifacts/spec-13-4-fixed-source-audit-track.md` exists;
    the reviewer searched only the tracked `planning-artifacts/specs/` promotion target,
    which this repo's own convention populates AFTER the story merges, not before); the
    memlog's test-pass counts are "self-reported with no CI link" (independently
    re-verified live against the same commands during this review pass — see Verification
    below — and this workflow's verification model is live re-run, not external CI).

## Design Notes

**Why the declared list lives in `parameters.yml`, not a new seed file/dataset type.** The
`seed_gaps` pipeline's precedent (`seed_lts_registry`, `seed_cwe_categories`) reads hand-curated
git-tracked files via `yaml.YAMLDataset`/`json.JSONDataset` — but those live under a shared
`seed_root` (`.claude/skills/conda-forge-expert/data`) because they are genuinely CFE-domain
artifacts reused cross-project. The org-audit list is atlas's own discovery input with no
cross-project reuse case, and it is small (~10 rows). `parameters.yml` already carries the
identical "injected, hand-edited, git-tracked declared config" shape for `ttls:` — reusing it
avoids inventing a new dataset type or file path for a handful of strings (Simplicity First).

**Why `classify_trending_candidates` is reused with no rename.** Kedro's `node(inputs=[...])`
binds positionally, not by parameter name — the function's parameter being named
`trending_candidates` while a pipeline node feeds it `org_audit_candidates` has zero runtime
effect. Renaming a parameter purely for cosmetics would touch code that has already survived
four adversarial review passes, for no behavior change (Surgical Changes). This IS the literal
mechanism CAP-4's intent describes: "reusing CAP-2's classifier instead of a one-off manual
audit."

**Why the seed list is populated, not left empty.** `org-audit-precedent.md`'s "material gaps"
candidates are the only declared list any planning artifact names. SPEC.md's non-goal —
"Treating the June-2026 org-audit package list as committed current scope" — warns against
trusting the list's OLD, implied classification, not against reusing its repo names as seed
data: every run re-verifies fresh against whatever `pypi_conda_mapping`/`pypi_universe`/
`pypi_intelligence_enriched` currently hold, so a candidate that has since shipped
independently classifies to `skip`/`already-on-conda-forge` automatically — this literally
demonstrates FR-67. The seed remains config-only, freely edited or replaced for a future
org-audit batch with no code change (SPEC.md assumption: "a reusable workflow ... not a
one-off manual sweep frozen at the June 2026 snapshot").

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done`.

**Implemented change.** Two more nodes in `pipelines/upstream_discovery/`:
`load_org_audit_candidates` (pure `params:org_audit_candidates -> pd.DataFrame` loader
over a git-tracked, hand-curated list seeded with `org-audit-precedent.md`'s June-2026
Microsoft "material gaps" candidates) and `classify_org_audit_candidates` (the SAME
`classify_trending_candidates` function from Story 13.2, reused unchanged, bound via
Kedro's positional `inputs=[...]` to `org_audit_candidates` instead of
`trending_candidates`) — producing `org_audit_candidates_classified` with the identical
tiered/reasoned shape. A candidate that has since shipped independently to
conda-forge now classifies to `tier="skip"`/`reason="already-on-conda-forge"`
automatically on every run (FR-67's literal contract), proven by a dedicated test.

**Files changed**
- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- new
  `load_org_audit_candidates`; `classify_trending_candidates` untouched.
- `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` -- two more `node(...)`
  entries.
- `conf/base/parameters.yml` -- new `org_audit_candidates:` declared list.
- `conf/base/catalog.yml` -- two new entries (`org_audit_candidates` raw,
  `org_audit_candidates_classified` derived) + two CAP-4-pending comments updated.
- `src/pyforge/atlas/orchestration/definitions.py` -- two `NODE_TIMEOUTS` entries.
- `tests/catalog/conftest.py` -- new `org_audit` domain prefix; pipeline/total counts
  bumped.
- `tests/pipelines/upstream_discovery/test_nodes.py` -- 8 new tests (happy path, dedup,
  never-silent-drop for malformed entries, empty/`None`/non-list degradation, and two
  classifier-reuse tests: the shipped-since-drop contract and a malformed-entry-surfaces-
  as-a-visible-skip-row proof).
- `_bmad-output/.../specs/spec-pyforge-atlas/.memlog.md` + `scripts/.spec-surface-baseline.json`
  -- two reconciling entries (initial landing + review-pass patches), each followed by a
  scoped baseline re-stamp.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- 2 new entries (pre-existing
  Story 13.2 classifier limitations, surfaced incidentally by this story's review).

**Review findings breakdown.** Blind Hunter (`bmad-review-adversarial-general`) and Edge
Case Hunter (`bmad-review-edge-case-hunter`) ran independently, without shared context,
against the full diff. 12 findings total, 0 intent_gap, 0 bad_spec: 3 patch (medium 1,
low 2) -- all applied; 2 defer (medium 2) -- appended to `deferred-work.md`, both
pre-existing Story 13.2 classifier limitations (PyPI-less candidates like Rust/Go CLIs
can never reach tier 2; the exact-repo-name-match resolution heuristic false-negatives
when a repo's real PyPI name differs, demonstrated by `org-audit-precedent.md`'s own
`agent-framework-core`/`microsoft/agent-framework` split) newly exercised by a
fixed-source batch, not introduced by this diff; 7 reject (low 7) -- reasoned
disagreement with already-documented spec decisions (the seed-list committed-scope
question, the `seed_lts_registry`-pattern alternative, CAP-4-before-CAP-5/CAP-3
sequencing — all explicitly reasoned through in this spec's own Design Notes or Never
section), one false claim (a cited spec file "doesn't exist" -- it does, at
`_bmad-output/implementation-artifacts/spec-13-4-fixed-source-audit-track.md`, simply
not yet promoted to the tracked location per this repo's post-merge promotion
convention), and one process point already independently re-verified (self-reported test
counts -- re-run live during this review pass with identical results).

**Patches applied.** `load_org_audit_candidates` no longer silently drops a malformed
list entry -- every entry now produces exactly one row (`repo_full_name=None` when
unextractable), matching `classify_trending_candidates`'s own "never a silent drop"
invariant one seam earlier, so a hand-edit typo in `parameters.yml` now surfaces as a
visible `skip`/`no-pypi-artifact` row instead of vanishing. Added case-insensitive dedup
(`casefold()`, first occurrence's casing kept). Corrected a transcription error in the
landing memlog entry (8 of 9 seeded candidates had lost their `microsoft/` prefix in the
prose summary; the actual `parameters.yml` data was always correct).

**Verification performed**
- `pixi run --frozen -e pyforge-atlas pytest tests/pipelines/upstream_discovery -q` --
  **57 passed** (54 at initial implementation, +3 from the review-pass patches).
- `pixi run --frozen -e pyforge-atlas kedro-test` -- **1054 passed, 19 skipped** (1042
  before this story).
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` -- **47 passed**.
- `pixi run --frozen -e pyforge-atlas dagster-dryrun` -- **58 passed** (confirmed live
  that `bootstrap_ops = node_ops - PHASE_P_OPS` picks up both new nodes automatically --
  no `SCHEDULED_JOBS` change needed).
- `python3 scripts/spec_surface_check.py` -- `OK: every tracked file governed or
  allowlisted; no drift` (both before and after the review-pass patches, each following
  its own scoped `.memlog.md` reconcile + baseline re-stamp).
- Every diff hunk independently re-verified against the actual file contents (not just
  the implementation subagent's report) before marking tasks complete.

**Residual risks.** The two deferred items are real, pre-existing limitations of the
Story 13.2 classifier (not this story's new code) that become more consequential for a
fixed-source audit batch than for the trending feed: a genuinely PyPI-less compiled/CLI
candidate can never reach tier 2, and a repo whose real PyPI package name differs from
its own repo name false-negatives to `no-pypi-artifact`. Both are visible to a human via
the `reason` column and already named as future classifier-seam work. CAP-3's operator
surface does not yet expose `org_audit_candidates_classified` (deliberately out of this
story's scope, per its Never section) -- querying it is Story 13.5's or a future CAP-3
extension's job.

**Follow-up review recommendation:** `false` -- one review pass found a modest,
localized patch set (1 medium + 2 low, all confined to one new function and its tests),
fully addressed and verified; the two defers are well-understood, already-documented,
low-urgency classifier-seam limitations, not open questions about this diff's own
correctness.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `12-4-fixed-source-audit-track-fr-67: done`).
