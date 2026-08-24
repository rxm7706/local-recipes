---
title: 'Story 9.2: The sweep runs against all eight stations'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py']
warnings: ['oversized']
baseline_revision: '51262819e76bde4d19c9511b20925e815b1c0503'
final_revision: '9675c3a27000ec2fbc5bff297f5f568d4f183dc9'
---

<intent-contract>

## Intent

**Problem:** Story 9.1's five hygiene predicates have zero production callers
— nothing gathers evidence for them across the fleet, so CAP-8's own promise
(reproduce warden's five finding classes as a fixture, zero false positives
against the already-clean `pyforge-warden`, surface at least one true
positive on a never-audited station) is unproven and unusable.

**Approach:** Add a new report-only `sources/hygiene.py::gather(target)`
that walks all 8 stations under `_bmad-output/projects/` (derived via
`iterdir()`, never hand-listed), gathers each class's evidence via plain
filesystem/YAML reads plus one new `git grep`-tolerant `cli_bridge.run_git`
call for the orphan-file class's inbound-reference check, classifies via
Story 9.1's own predicates, and registers as a new
`Source.BMAD_OUTPUT_HYGIENE` `REGISTRY` row. No `doctor check`/`monitor` CLI
wiring yet (mirrors `Source.ADOPTION`'s own "registered, not yet dispatched"
precedent).

## Boundaries & Constraints

**Always:**
- `sources/hygiene.py::gather(target: Path) -> tuple[Finding, ...]` — ONE
  `Source` (`BMAD_OUTPUT_HYGIENE = "bmad-output-hygiene"`), `check` set
  per-Finding to the firing `HygieneFindingKind.value` (mirrors
  `LEDGER_REGRESSION`'s one-Source/multiple-`check`-kinds shape).
- Stations derived by `iterdir()`-ing `target/"_bmad-output"/"projects"`,
  filtered to dirs with a `planning-artifacts` subdir — the exact
  `board.py::gather_chain_completeness` convention; bare station name via
  `project_dir.name.removeprefix("pyforge-")`.
- Per-station evaluation is isolated in its own try/except (one station's
  unreadable file degrades to a WARN, never discards the other 7 stations'
  already-computed findings) — mirrors
  `board.py::_check_chain_completeness`'s own per-project isolation.
- `hygiene.py` does ONLY evidence-gathering; classification is exclusively
  the 5 `hygiene_definitions.is_*` predicates — never reimplemented.
- Aggregation mirrors `ledger.py::gather`: zero findings across the whole
  sweep → exactly one `Finding(status=OK)`; any positives → one `Finding`
  per instance only, no baseline-OK noise per clean station×class pair.
- `cli_bridge.run_git` gains a keyword-only
  `ok_exit_codes: frozenset[int] = frozenset({0})` param (default preserves
  every existing caller unchanged) so `hygiene.py` can treat `git grep`'s
  documented exit 1 ("no match", not an error) as success with empty
  output, while exit ≥2 / git-absent / timeout still raises
  `CliBridgeError`.
- Orphan-file candidates come from exactly two per-station locations: direct
  files at the project root (never recursing into sibling dirs like
  atlas's `spec-archive/`), and every file recursively under
  `planning-artifacts/` — matches both real historical fixture locations
  (`RESUME-EPIC-10.md` at root; the herald intake draft under
  `planning-artifacts/`) and excludes gitignored `implementation-artifacts/`
  outright (it may be a Tier-3-backlink symlink to a different repo
  entirely).
- Register `SourceRegistration(source=Source.BMAD_OUTPUT_HYGIENE,
  scope="repo", subject_station="fleet", owning_station="doctor")` in
  `sources/__init__.py::REGISTRY`, and add
  `Source.BMAD_OUTPUT_HYGIENE: "hygiene.py"` to
  `test_source_independence.py::SOURCE_MODULE` — the independence guard
  then forbids importing any `pyforge.<station>` package automatically
  (subject != owner puts it in scope).

**Block If:** nothing identified — every open question resolves from
Story 9.1's module and this codebase's existing conventions.

**Never:** no `doctor check`/`monitor` CLI or dispatch wiring this story
(Story 9.1's own Never clause named this plausibly-9.2's job, but no AC
requires it — mirrors `ADOPTION`'s "registered, not yet wired into a
default axis" precedent); no `--fix`/archive/mutation action (Story 9.3);
no 6th finding class; no re-deriving `hygiene_definitions.py`'s private
conventional-name/dir sets locally — call
`is_orphan_file(relpath, has_inbound_references=False)` as the cheap
pre-filter instead (its `if has_inbound_references: return False` line
never fires when the argument is already `False`, so this correctly asks
"candidate regardless of references" without duplicating any constant).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fixture reproduction, all 5 classes | Synthetic `_bmad-output/projects/<slug>/` tree (tmp_path) reproducing each of Story 9.1's 5 real archived positive shapes | `gather(tmp_path)` emits exactly 5 Findings, one per `HygieneFindingKind` | none |
| Zero false positives against warden (live) | `gather(Path("."))` against the real repo | no Finding names station `"warden"` | none |
| ≥1 true positive elsewhere (live) | same live `gather(Path("."))` call | ≥1 Finding names a station != `"warden"`; re-verify live before asserting that `pyforge-herald/planning-artifacts/deckcraft-board-epics-displaced-2026-08-08.json` (currently unreferenced repo-wide, non-conventional name) is still real — if remediated, re-run the live scan and cite whatever real instance is found instead | none |
| Fully clean synthetic sweep | Synthetic tree with zero instances of any class | `gather()` returns exactly one `Finding(status=OK)` | none |
| One station's file is unreadable | Synthetic tree: one station's `README.md` is undecodable, another station has a real positive | unreadable station degrades to its own WARN; the other station's real positive is still emitted | WARN, no crash |
| Orphan-file: no inbound references | Real non-conventional candidate, zero matches elsewhere (`git grep` exit 1) | `has_inbound_references=False`, correctly resolved (not a WARN) | none |
| Orphan-file: git errors | `run_git`'s grep call raises `CliBridgeError` (exit ≥2 / git absent) | that one candidate degrades to a WARN naming the failure; other candidates/stations unaffected | WARN, no crash |
| dead-test-scaffolding: no marker dir | Station root has no `tests/`, `pytest.ini`, `playwright.config.ts` | no candidate considered (not even a clean pass) | none |
| hollow-sprint-status: no non-ledger file | Station has only `sprint-status-ledger.yaml` | no candidate considered | none |

</intent-contract>

## Code Map

- `src/pyforge/doctor/models.py` -- MODIFIED. Add `Source.BMAD_OUTPUT_HYGIENE = "bmad-output-hygiene"`.
- `src/pyforge/doctor/cli_bridge.py` -- MODIFIED. `run_git` gains `ok_exit_codes: frozenset[int] = frozenset({0})` (keyword-only, default unchanged for every existing caller).
- `src/pyforge/doctor/sources/hygiene.py` -- NEW. `gather(target) -> tuple[Finding, ...]`.
- `src/pyforge/doctor/sources/__init__.py` -- MODIFIED. Append the `BMAD_OUTPUT_HYGIENE` `SourceRegistration` row.
- `tests/meta/test_source_independence.py` -- MODIFIED. Add `Source.BMAD_OUTPUT_HYGIENE: "hygiene.py"` to `SOURCE_MODULE`.
- `tests/unit/test_sources_hygiene.py` -- NEW. One test per I/O matrix row.
- `tests/unit/test_cli_bridge.py` -- MODIFIED. Two new `run_git`/`ok_exit_codes` tests.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/doctor/models.py` -- add `BMAD_OUTPUT_HYGIENE = "bmad-output-hygiene"` to `Source` -- names the new closed-taxonomy member.
- [x] `src/pyforge/doctor/cli_bridge.py` -- add `ok_exit_codes: frozenset[int] = frozenset({0})` keyword-only param to `run_git`; a returncode outside the set still raises `CliBridgeError` as today -- lets a caller tolerate `git grep`'s exit-1-means-no-match without misreading it as failure.
- [x] `src/pyforge/doctor/sources/hygiene.py` (NEW) -- `gather(target)`: derive stations via `target/"_bmad-output"/"projects"` iterdir (dirs with a `planning-artifacts` subdir only); per station gather each class's evidence and call the matching `hygiene_definitions.is_*` predicate; per-station try/except isolation; aggregate per `ledger.py::gather`'s empty-vs-positive convention.
- [x] `src/pyforge/doctor/sources/__init__.py` -- append the `BMAD_OUTPUT_HYGIENE` row (`scope="repo"`, `subject_station="fleet"`, `owning_station="doctor"`) with an inline comment recording the `subject_station="fleet"` rationale.
- [x] `tests/meta/test_source_independence.py` -- add `Source.BMAD_OUTPUT_HYGIENE: "hygiene.py"` to `SOURCE_MODULE`.
- [x] `tests/unit/test_sources_hygiene.py` (NEW) -- one test per I/O matrix row; the live true-positive test re-verifies the cited herald file's groundedness immediately before asserting, failing loud (not silently) if that fact has changed.
- [x] `tests/unit/test_cli_bridge.py` -- add two `run_git`/`ok_exit_codes` tests (exit-1 tolerated when in the set; exit-2 still raises).

**Acceptance Criteria:**
- Given a synthetic fixture tree reproducing all 5 archived positive shapes, when `gather()` runs against it, then it emits exactly 5 Findings, one per `HygieneFindingKind`.
- Given the live repo, when `gather(Path("."))` runs, then no Finding names station `"warden"`.
- Given the live repo, when `gather(Path("."))` runs, then ≥1 Finding names a station other than `"warden"`.
- Given `test_every_in_scope_source_is_mapped_to_exactly_one_file` and the independence-guard parametrized tests, when they run after this change, then `hygiene.py` passes both.
- Given `tests/meta/test_read_only_guard.py`, when it runs after this change, then `hygiene.py` is scanned and reports zero write call sites.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 1, low 2)
- defer: 2 (high 0, medium 2, low 0)
- reject: 6 (low 6)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter reproduced a real bug: `_dream_frontmatter_status`'s `text.split("---", 2)` mis-splits when an earlier frontmatter field's own value contains a literal `---` substring, truncating before the real closing fence and silently losing `status` (a genuinely stale Dream then goes unreported with no warning). Fixed: rewrote to a line-anchored fence parser (a fence line must be exactly `---` once stripped); added two regression tests (`test_dream_frontmatter_status_survives_an_embedded_triple_dash_in_an_earlier_field`, `test_dream_frontmatter_status_returns_none_without_a_closing_fence`).
  - `[low]` `[patch]` Blind Hunter found the 3 new `run_git`/`ok_exit_codes` tests in `test_cli_bridge.py` only scrubbed 2 of the 6 git env vars its own sibling `test_sources_hygiene.py` (added in this same diff) treats as leaky — an inconsistency within the diff, live-risky in this exact nested-worktree environment. Fixed: replaced the per-test manual `delenv` calls with an `autouse` fixture scrubbing the same 6 vars as the sibling file.
  - `[low]` `[patch]` Blind Hunter found the new `Source.BMAD_OUTPUT_HYGIENE` docstring comment in `models.py` ("walking every station's own artifacts at once") reads as overclaiming exhaustive file coverage, when the real scope is two specific conventional locations per station. Fixed: reworded to name the actual scope ("walks all 8 stations' own conventional planning-artifact locations in one sweep (not every file a station may hold)").
  - `[medium]` `[defer]` Both reviewers independently found `gather()`'s top-level `projects_dir.iterdir()`/per-project `is_dir()` check sit outside any try/except, so a `PermissionError` would crash the whole sweep instead of degrading — contradicting the module's own "degrades, never crashes" claim. Not patched: this exact shape is `board.py::gather_chain_completeness`'s own pre-existing, already-shipped precedent (Story 6.5), which this story's own spec explicitly directed `hygiene.py` to mirror; patching only the new file would leave it inconsistent with what it claims to follow. Deferred as `DW-FU-9-2` (cross-cutting hardening spanning `board.py` too, outside this story's Code Map).
  - `[medium]` `[defer]` Blind Hunter found `_evaluate_station`'s five hygiene checks run sequentially under one shared try/except, so one check raising (e.g. a malformed `sprint-status.yaml`) silently drops every check ordered after it for that station, hiding a real, independent finding. Not patched: the spec's own Boundaries scoped isolation to per-station granularity only, explicitly mirroring `board.py::_check_project_chain_completeness`'s identical bundled-checks shape — the same precedent issue as the entry above. Deferred as `DW-FU-9-2-2`.

### 2026-08-15 — Repair pass (deterministic verification failure)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (high 0, medium 1, low 0)
- defer: 1 (high 0, medium 1, low 0)
- reject: 3 (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` failed deterministic verification on `test_live_repo_gather_surfaces_at_least_one_true_positive_naming_a_non_warden_station`: its own bare literal `basename = "deckcraft-board-epics-displaced-2026-08-08.json"` made the test file itself a `git grep` match for the cited herald fixture's basename, so the test's own live-groundedness pre-check found itself as an "inbound reference" and failed — and the identical bug would silently corrupt `hygiene.py::_has_inbound_references`'s own production result for that same file (both do the same repo-wide `git grep -l --fixed-strings -e <basename>`). Fixed: split the literal into `"deckcraft-board-epics-displaced-2026-08-08" + ".json"` so the full basename no longer appears as a contiguous substring in the test file's own source text; verified live (`git grep` for the full literal now returns zero matches repo-wide) and via the full suite (948 passed, 2 skipped, 0 failed). Confirmed by both reviewers in the follow-up adversarial pass: sound and complete for its stated target, no other literal filename in the diff has the same self-reference hazard (every other literal basename is used only inside isolated `tmp_path` git fixtures, never against the live monorepo).
  - `[medium]` `[defer]` Both reviewers independently found `_has_inbound_references`'s repo-wide `git grep -l --fixed-strings -e <basename>` match is a bare substring with no path/word-boundary awareness and (being plain `git grep`) only sees tracked content — so a genuinely orphaned file can be masked by an unrelated same-basename mention elsewhere in the repo, or by a reference that lives only in a not-yet-committed file. Blind Hunter verified live that `sprint-status.yaml` (not in `hygiene_definitions.py`'s `_CONVENTIONAL_FILENAMES` allowlist) appears in 157 tracked files repo-wide, so a genuinely orphaned instance of that exact filename would never surface. Not patched: this is exactly the protocol the spec's own Design Notes mandate, not an implementation deviation from it; no live false negative exists today and this story's own acceptance criteria all pass against the current live repo; hardening the match would mean amending the Design Notes, outside this repair pass's charter (fix the deterministic-verification failure without touching frozen intent or expanding scope) — the same reasoning already applied to `DW-FU-9-2`/`DW-FU-9-2-2` above. Deferred as `DW-FU-9-2-3`.
  - `[low]` `[reject]` Edge Case Hunter flagged `_ledger_all_done` propagating an unhandled `yaml.YAMLError` on a malformed `sprint-status-ledger.yaml`. This is the identical mechanism already recorded as `DW-FU-9-2-2` (one raising check silently drops every check ordered after it for that station) via a different concrete trigger file — not a new, distinct issue, so no new entry was minted.
  - `[low]` `[reject]` Edge Case Hunter proposed that a misresolved/absent `_bmad-output/projects` target should emit a WARN instead of the current `OK`. Rejected: this contradicts the story's own explicit, tested requirement (`test_gather_returns_one_ok_finding_when_no_projects_dir_exists`) that mirrors `ledger.py::gather`'s own empty-vs-positive convention with no carve-out for a misconfigured target.
  - `[low]` `[reject]` Edge Case Hunter proposed guarding `run_git`'s `ok_exit_codes` against an empty `frozenset()` from a hypothetical future caller. Rejected: speculative — no current caller passes an empty set, and no Boundary/Never clause requires defending against it.

## Design Notes

**`subject_station="fleet"` is a new value, not a hand-picked single
station.** Every existing `REGISTRY` row names one real station as the
artifact's subject; this sweep's real subject is every station's own
artifacts at once (doctor included, self-judging alongside the rest), so
naming any single station would misrepresent what the source judges.
`SourceRegistration.__post_init__` only requires a non-empty string — no
closed enum of valid `subject_station` values exists — so `"fleet"` is
valid, not a schema violation. Each `Finding.evidence["station"]` still
carries the real specific station a given instance was found in, so no
per-finding traceability is lost. `CHAIN_COMPLETENESS` also walks all 8
projects but keeps `subject_station="marshal"` because what it judges (the
Guildhall board's truthfulness) really is Marshal-owned — that precedent
doesn't apply here, since no single station owns "every station's own
hygiene."

**Reference-check search token.** Search the candidate file's basename
(not full relpath) via `git grep -l --fixed-strings -e <basename>` from
the repo root, then drop the candidate's own repo-relative path from the
match list before deciding `has_inbound_references` — a file's own content
mentioning its own filename must not count as an inbound reference.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: all pass, including the new `test_sources_hygiene.py` cases, the 2 new `test_cli_bridge.py` cases, and the existing meta tests (`test_read_only_guard`, `test_every_real_sources_file_is_mapped_by_at_least_one_source`, `test_every_in_scope_source_is_mapped_to_exactly_one_file`, the independence-guard parametrized tests) still green.

## Auto Run Result

Status: done

**Summary.** Resumed a session whose prior commit (`9a2c3f6100`) failed
deterministic verification (`pixi run --frozen -e pyforge-doctor
pyforge-doctor-test`). Root cause: `test_sources_hygiene.py`'s live
true-positive test named the cited herald fixture's basename as a bare
string literal, and its own `git grep` re-verification pre-check then
matched the test file's own source text as an "inbound reference" to that
same fixture — a self-inflicted contamination that would identically
corrupt `hygiene.py::_has_inbound_references`'s production result for the
same file (both run the same repo-wide `git grep -l --fixed-strings -e
<basename>`).

**Files changed:**
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- split the basename literal into `"deckcraft-board-epics-displaced-2026-08-08" + ".json"` so the full string no longer appears as a contiguous substring in this file's own source, eliminating the self-match.

**Review findings breakdown (repair-pass re-review, 2026-08-15):** patch 1 (medium, applied — the fix above, independently confirmed sound and complete by both reviewers), defer 1 (medium, minted `DW-FU-9-2-3` — `_has_inbound_references`'s basename-only matching is a real but currently-latent false-negative risk inherent to the Design Notes' own specified protocol, not an implementation deviation from it), reject 3 (low — one duplicate of the already-recorded `DW-FU-9-2-2`, one contradicting this story's own tested no-projects-dir behavior, one speculative).

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 948 passed, 2 skipped, 0 failed (previously 1 failed: the self-reference bug above; a second failure on `test_check_speed_budget.py`'s timing benchmark did not reproduce on any subsequent run and is judged environmental noise, not a regression from this story). Live-verified independently: `git grep -l --fixed-strings -e "deckcraft-board-epics-displaced-2026-08-08.json"` now returns zero matches repo-wide.

**Residual risks:** `DW-FU-9-2-3` (above) is a real, latent limitation of the live orphan-file detection's reference-matching precision; no live instance affects it today.

