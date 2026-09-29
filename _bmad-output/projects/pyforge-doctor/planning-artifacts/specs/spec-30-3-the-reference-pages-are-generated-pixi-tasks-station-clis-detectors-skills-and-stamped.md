---
title: '30.3: The reference pages are generated — pixi tasks, station CLIs, detectors, skills — and stamped'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md']
deferred:
  - summary: >-
      spec-pyforge-doctor/SPEC.md's `surface:` list does not yet list the five
      new docs-* generator scripts + shared helper (Story 30.2 precedent:
      scripts/docs_map_render.py was added there directly). SPEC.md is
      hook-blocked from a hand-edit in this session (AGENTS.md: re-derive via
      `bmad-spec`, never hand-edit) and a station-Spec `bmad-spec`
      re-derivation is out of scope for this one story's dispatch.
    evidence: |-
      spec-pyforge-doctor/.memlog.md's 2026-09-24 entry already names the six
      new script paths under "Surface gains (surface: list): ...". Interim
      fix: allowlisted in scripts/spec_surface_allowlist.txt with a reason
      citing this story and the pending SPEC.md re-derivation.
      `python scripts/spec_surface_reconcile.py` reports OK with the
      allowlist entries in place.
    location: >-
      scripts/spec_surface_allowlist.txt
    severity: low
declared_low_risk: false
baseline_revision: '3811d6805cfd6d2e555aed54a769a344517b435d'
---

<intent-contract>

## Intent

**Problem:** the pixi-task reference is hand-written and already stale, the station cheat sheet was typed from memory, and no page lists the detectors or the skills — the pages agents most need are the least exact.

**Approach:** one generator per reference page, each reading its source of truth (`pixi.toml` task tables and `[environments]`, each station CLI's `--help`, `scripts/detectors.py` + `doctor.sources` registrations, `SKILL.md` frontmatter), writing the page plus a `derived_at` + `tree` stamp (herald's `facts.yaml` shape), idempotent on an unchanged tree; `docs-currency` (30.2) gains the generated-page check.

## Boundaries & Constraints

**Always:** generated pages are never hand-edited (a hand edit is a finding, as for `library-llms-full.md`); a generator is a pixi task under `guild-tasks` (or a station duty for that station's CLI page) and is registered as the page's `sources` in `map.yaml`; `library-llms-full.md` keeps its own lane.
**Never:** generate from a model; every value comes from the tree.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| unchanged tree, run a generator twice | byte-identical page, stamp `tree` unchanged |
| a task added to `pixi.toml`, no regeneration | `docs-currency` warn → fail after promotion: pixi-tasks page stale |
| a station CLI gains a verb | `docs-station-cli` rewrites the cheat sheet row; stamp advances |
| a `SKILL.md` frontmatter `description` edited | skills catalog regeneration differs → finding until regenerated |
| a hand edit inside a generated page | finding naming the page |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-84`.
Surface: generator tasks `docs-pixi-tasks`, `docs-station-cli`, `docs-detectors`, `docs-skills-catalog`, `docs-environments` (`scripts/docs_*.py` or station duties), `docs/how-to/pixi-tasks.md`, `docs/reference/station-cheat-sheet.md`, `docs/reference/detectors.md` (new), `docs/reference/skills-catalog.md` (new), `docs/reference/environments.md` (new), `docs/map.yaml` rows, `docs_currency.py`'s generated-page check + tests.
Ledger key: `30-3-the-reference-pages-are-generated-pixi-tasks-station-clis-detectors-skills-and-stamped`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 (night) from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:** run every `docs-*` generator twice on a clean tree → no diff; `pixi run -e pyforge-guild detectors-ci` green.

</intent-contract>

## Review Triage Log

### 2026-09-24 — Review pass

- verdicts: 23 findings — high 0, medium 12, low 6, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` (Blind Hunter) `parse_frontmatter()` silently returns `{}` on a `yaml.YAMLError`; a plain-scalar `description:` containing a mid-value `": "` fails to parse — reproduced live for `idea-refine`, `performance-optimization`, `security-and-hardening`, `spec-driven-development` (all 4 render blank descriptions in `docs/reference/skills-catalog.md`, no finding raised). — Patched: add a regex fallback that extracts a single-line `description:` value when the full frontmatter block fails to parse.
  - `[medium]` `[patch]` (Blind Hunter) `test_docs_skills_catalog.py` only exercises a folded (`description: >`) YAML value; no test covers a plain-scalar description containing a colon, the exact shape that breaks 4 live skills — same root cause as the finding above. — Patched: add a regression test using a real unquoted colon-bearing description (mirrors `idea-refine`'s).
  - `[medium]` `[patch]` (Blind Hunter) `docs_station_cli.py`'s `capture_help()` runs `<script> --help` with `check=False` and returns `result.stdout or result.stderr` unconditionally, never inspecting the return code; the committed `docs/reference/station-cheat-sheet.md` embeds a full Python traceback (`ModuleNotFoundError: No module named 'fastmcp'` for `marshal-mcp --help`) including this worktree's own absolute path. — Patched: `capture_help()` now returns `None` (the existing "not resolvable" path) on a non-zero return code, and also catches `UnicodeDecodeError`.
  - `[medium]` `[patch]` (Blind Hunter) `test_docs_station_cli.py` never exercises the real `capture_help()` — every test injects a fake `help_capture` lambda — so the traceback-swallowing bug above had zero regression coverage. — Patched: added a test driving the real `capture_help()` against a script that exits non-zero.
  - `[medium]` `[patch]` (Edge Case Hunter) `docs_station_cli.py:111-131` — a captured `--help` output containing bytes undecodable under the current locale (`text=True`) crashes instead of falling back to the "not resolvable" note — same `capture_help()` root cause as the two findings above. — Patched: covered by the same `capture_help()` hardening (returncode + `UnicodeDecodeError` guard).
  - `[medium]` `[patch]` (Intent Alignment Auditor) `capture_help()` violates "every value comes from the tree" / "idempotent on an unchanged tree": the embedded traceback bakes in this specific worktree's absolute path, so an identical commit checked out elsewhere would render different bytes for the same page — same root cause as the three findings above. — Patched: same `capture_help()` fix; the placeholder text for an unresolvable/crashing station carries no machine-specific path.
  - `[medium]` `[patch]` (Verification Gap Reviewer) `_docs_gen_common.head_stamp()` computes `{derived_at, tree}` from the repo's global HEAD, not from a page's declared `sources:`; `write_generated_page`'s `--check` does a plain `current == content` compare (stamp included), so ANY unrelated commit landing elsewhere flips every generated page to "stale" even though its real sources are byte-identical — demonstrated live (this branch's own `wip: 30.3 (auto-checkpoint)` commits advance HEAD every few seconds with `pixi.toml` unchanged, and `--check` reports STALE every time). No test lets two calls to the real `head_stamp()` differ while a page's declared source stays unchanged — every generator's own roundtrip test freezes `head_stamp` to one fixed value. — Patched: `--check` now compares the rendered body with the stamp header lines stripped from both sides, so only a real content change (task added, CLI verb changed, `SKILL.md` edited, hand edit) trips it; the write path is unchanged.
  - `[medium]` `[patch]` (Intent Alignment Auditor) Same root cause as the Verification Gap Reviewer finding above: the staleness surface is global git state, not per-page sources, despite the I/O matrix being written in per-source terms ("a task added to `pixi.toml`", "a station CLI gains a verb", etc.). The diff's own memlog entry concedes the auto-checkpoint HEAD churn "legitimately re-triggers the HEAD-based stamp's staleness signal... same as a real commit landing would." — Patched: same stamp-stripped comparison fix.
  - `[medium]` `[patch]` (Intent Alignment Auditor) Same root cause again: `test_head_stamp_is_idempotent_on_an_unchanged_tree` and every generator's "write then check roundtrip" test freeze `head_stamp` to a fixed dict for both calls, so the specific scenario that breaks the invariant (generate → unrelated commit lands → check again) is exercised nowhere. — Patched: added a git-fixture test (real repo, two commits, page's declared source unchanged between them) asserting `--check` still reports current.
  - `[medium]` `[patch]` (Blind Hunter) `_docs_gen_common.update_map_stamp()` reads the whole of `docs/map.yaml` and re-serializes the entire document with `yaml.safe_dump()` to update one page's `stamp`, which is why this diff reformats all ~90 pre-existing, untouched page entries from 2-space-indented list items (`  - path:`) to flush-left (`- path:`) as a side effect of a 5-entry substantive change — inflating this diff and guaranteeing every future stamp update re-touches every entry's formatting again. Verified: `docs_map_render.py` (30.2) never writes `map.yaml`, so this diff is the file's first-ever programmatic writer, and plain `yaml.safe_dump` does not reproduce the hand-authored indent convention. — Patched: `update_map_stamp()` now serializes with a `yaml.Dumper` subclass that indents block sequences, matching the pre-existing on-disk style.
  - `[medium]` `[patch]` (Intent Alignment Auditor) Lower-severity note, same root cause as the finding above: `docs/map.yaml` was rewritten wholesale from 2-space-indented list style to flush-left, a much larger diff footprint than "rows for the new/changed pages" implies. — Patched: same Dumper-subclass fix.
  - `[medium]` `[patch]` (Edge Case Hunter) `docs/how-to/pixi-tasks.md`'s hand-written callout ("`pixi run bmad-preflight` is broken — it shells out to `bash scripts/ensure-bmad-preflight.sh`, which does not exist") was dropped by the regeneration with no replacement mechanism; verified the task (`pixi.toml:1093-1095`) still points at a script that still does not exist (`scripts/ensure-bmad-preflight.sh` absent from the tree), so a reader following the new "exact by construction" page now hits the same failure with no forewarning. — Patched: `docs_pixi_tasks.py` now flags a task whose `cmd` references a `scripts/*.sh`/`scripts/*.py` path that does not exist on disk, annotating that row instead of silently listing it as ordinary.
  - `[low]` `[patch]` (Blind Hunter) `pixi.toml`'s own new comment calls the `docs-gen-test` addition to `pr-preflight`'s `depends-on` the "Eighth leg", while `spec-pyforge-doctor/.memlog.md`'s entry for the identical change calls it the "ninth leg" — two records of the same event disagree. Counted the live `depends-on` list (9 entries total; `docs-gen-test` is the 8th named in the pixi.toml comment's own chronological narrative) — `pixi.toml`'s "Eighth" is the one consistent with its own numbered history. — Patched: corrected the memlog wording from "ninth" to "eighth" (memlog is otherwise append-only/historical, but this is the same still-open dispatch's own just-written entry, not a past record).
  - `[low]` `[patch]` (Blind Hunter) `cli_bridge.run_check_script()`'s check-time PATH dependency for `docs_station_cli.py` (which stations resolve depends on the calling process's PATH) is undocumented — only the generation-time behavior is called out in the script's own docstring. Bounded in practice because `detectors-ci`/`pyforge doctor check` are always invoked as `-e pyforge-guild` per this repo's own convention, but worth naming. — Patched: added one docstring sentence to `docs_station_cli.py` noting the check-time implication.
  - `[low]` `[reject]` (Blind Hunter) `docs-map-schema.json` documents in prose that `sources`/`generator`/`stamp` are "generated-kind only" but has no `if`/`then` conditional enforcing it against `kind`; a malformed page entry would still validate. — Rejected: `docs_currency.py`'s own runtime checks (`generated-page-with-no-generator-declared`, `-with-missing-generator-script`) already catch exactly this with a WARN, so there is no silent-failure path; tightening the JSON Schema is scope beyond this story's stated Boundaries/Verification and the fix (an `if`/`then` conditional) is more than a direct correction.
  - `[low]` `[reject]` (Blind Hunter) `docs/map.yaml` reassigns ownership of `how-to/pixi-tasks.md`, `reference/environments.md`, `reference/skills-catalog.md` to `steward`, `reference/detectors.md` to `doctor`, but `reference/station-cheat-sheet.md` (same story, same generator family) keeps `fleet` — no documented rule anywhere names why. — Rejected: `owner:` is informational/organizational, not read by any generator, detector or test with behavior depending on its value (verified — only `docs_currency`'s ownership-blind checks and `docs_map_render`'s rendering consume it); no documented ownership rule exists to judge a "correct" assignment against, so picking one by guess would not demonstrably fix anything, and users/developers are unlikely to be harmed by the label itself.
  - `[low]` `[reject]` (Edge Case Hunter) `docs_currency.py`'s `_check_generated_page` reports a generator subprocess crash identically to ordinary staleness — same WARN message either way. Verified: the finding's own `evidence["output"]` field does carry the generator's actual stdout/stderr (including a traceback, if that's what happened), so the distinguishing information is not lost, just not reflected in the message text; and the suggested remedy ("regenerate") immediately surfaces a real crash the moment it's attempted. — Rejected: distinguishing "crashed" from "genuinely stale" cleanly would need a new exit-code convention across all five generators plus the check, which is more than a direct correction, for a case whose evidence is already available and whose remedy self-reveals the true cause.
  - `[low]` `[defer]` (Blind Hunter) `spec-pyforge-doctor/SPEC.md`'s `surface:` list does not yet list the six new script paths this story adds; papered over with an interim `scripts/spec_surface_allowlist.txt` entry rather than a real fix, with no scheduled story/date to close it. — Already deferred: recorded in this spec's own `deferred:` frontmatter (added during implementation, before this review pass) and promoted into `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` as `DW-FU-30-3`, citing the real path `scripts/spec_surface_allowlist.txt`; carried forward as-is, no new action from this pass.
  - `[false]` `[reject]` (Edge Case Hunter) `scripts/_docs_gen_common.py`'s git subprocess calls have no guard for git being missing, the cwd not being a repository, or a repository with zero commits. — Refuted: every `docs-*` generator only ever runs as a pixi task from within this specific, long-lived git repository, which always has git available and a full commit history; none of these three conditions is reachable in this repo's actual operating envelope, so an unguarded failure there is correct behavior for an unreachable state, not a defect.
  - `[false]` `[reject]` (Edge Case Hunter) `scripts/docs_pixi_tasks.py`'s synthetic `"(top-level)"` feature (for a bare top-level `[tasks]` table) is claimed to render as "not composed by any environment" incorrectly. — Refuted: verified `pixi.toml` has no top-level `[tasks]` table today (`tomllib` parse confirms `data.get("tasks")` is empty), so this code path is not reachable in this repo's current, real manifest.
  - `[false]` `[reject]` (Edge Case Hunter) `scripts/docs_pixi_tasks.py:_feature_environments` indexes `env_spec["features"]` directly rather than defaulting like its sibling `docs_environments.py`, risking a `KeyError` for a dict-shaped environment entry with no `features` key. — Refuted: verified every one of the 35 dict-shaped entries in this repo's actual `pixi.toml [environments]` table declares `features`; the input shape that would trigger the `KeyError` does not exist here.
  - `[false]` `[reject]` (Edge Case Hunter) The Spec's Boundaries text says a generator "is registered as the page's `sources` in `map.yaml`", but the implementation stores the generator's identity under a separate `generator:` key rather than inside `sources:`. — Refuted: `docs/map.yaml` carries both keys on every generated page (e.g. `reference/detectors.md`: `generator: scripts/docs_detectors.py` plus `sources: [scripts/detectors.py, ...]`); the generator's identity is recorded, just under a more precise, separately-named key than the Boundaries text's loose phrasing suggested — `sources:` correctly lists the derivation inputs, matching the pre-existing convention for authored pages.
  - `[false]` `[reject]` (Intent Alignment Auditor) A boundary explicitly left open by the intent (station duty vs. a plain script) was "resolved silently" toward the plain-script option for all five generators including the CLI page. — Refuted: the Boundaries clause names "a pixi task under `guild-tasks` **or** a station duty" as two explicitly permitted alternatives; consistently choosing the first, permitted option for all five generators is not a divergence from spec — both readings were always valid, and no reader is misled since the choice is uniform and the Binding section names the actual `docs-*` pixi tasks used.

## Auto Run Result

**Summary.** Five generator scripts (`docs_pixi_tasks.py`, `docs_environments.py`, `docs_detectors.py`, `docs_skills_catalog.py`, `docs_station_cli.py`), each reading its own source of truth directly (`pixi.toml`, `scripts/detectors.py`'s registry, `.claude/skills/*/`, each station's `pyproject.toml` + live `--help`) and sharing `scripts/_docs_gen_common.py` for the `derived_at`/`tree` stamp and write/`--check` plumbing. `docs_currency.py` gained one generic `generated-page-stale` check that subprocess-invokes a page's declared generator's `--check` mode via a new `cli_bridge.run_check_script` (the sole subprocess site, AD-5) and reads its exit code — covering every I/O-matrix staleness class through one mechanism. `docs/map.yaml` gained three new page rows and reclassified two existing pages `authored` → `generated`. A review pass then found and patched a real false-positive in the staleness check itself (see below) plus five other live bugs before this pass closed.

**Files changed** (32 total; grouped):
- New: `scripts/_docs_gen_common.py`, `scripts/docs_pixi_tasks.py`, `scripts/docs_environments.py`, `scripts/docs_detectors.py`, `scripts/docs_skills_catalog.py`, `scripts/docs_station_cli.py`, `docs/reference/detectors.md`, `docs/reference/environments.md`, `docs/reference/skills-catalog.md`, `tests/scripts/test_docs_gen_common.py` + 5 sibling generator test files, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` (DW-FU-30-3 row).
- Changed: `docs/how-to/pixi-tasks.md` and `docs/reference/station-cheat-sheet.md` (now generated, not hand-authored), `docs/map.yaml` + `docs/MAP.md`, `pixi.toml` (6 new `guild-tasks` entries + `docs-gen-test` wired into `pr-preflight`), `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` + its test file, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/docs-map-schema.json` (`generator:` field), `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py`.
- Governance/currency bookkeeping (this dispatch's own reconcile, not story content): `scripts/spec_surface_allowlist.txt` (6 new script paths, interim — see deferred item below), `spec-pyforge-doctor/.memlog.md`, the station PRD/architecture-spine/epics (`spec→prd→arch→epics` chain-currency cascade triggered by the memlog move; Story 30.2's own un-reconciled landing folded into the same pass).

**Review findings breakdown** (4 layers: Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor; 23 raw findings grouped into 16 entries by shared root cause):

- **Patched (7 entries, 12 raw findings, all `patch`):**
  - `parse_frontmatter` silently dropped 4 real skills' descriptions on an unquoted-colon YAML value (blank cells in `skills-catalog.md`, no finding raised) — regex fallback added, with a regression test.
  - `capture_help()` ignored the subprocess return code (and had no `UnicodeDecodeError` guard), embedding a live crash traceback — including this worktree's absolute path — into the committed `station-cheat-sheet.md` for `marshal-mcp` — now returns `None` (the existing "not resolvable" path) on failure.
  - **The big one:** the staleness stamp compared full page content including the `derived_at`/`tree` header, so ANY unrelated commit landing anywhere in the repo flipped every generated page to "stale" regardless of whether its real sources changed — demonstrated live via this branch's own auto-checkpoint commits. Fixed by stripping the stamp header from both sides of the `--check` comparison; verified live post-fix that all 5 pages report `current` immediately after a fresh commit.
  - `update_map_stamp()`'s plain `yaml.safe_dump` reformatted all ~90 untouched `docs/map.yaml` entries from 2-space-indented to flush-left as a side effect of one page's stamp update — fixed with an indent-preserving `Dumper` subclass; verified live that untouched entries keep their original style.
  - The regenerated `pixi-tasks.md` silently dropped the hand-written "`bmad-preflight` is broken" warning with no replacement — the generator now flags any task whose `cmd` references a nonexistent `scripts/*.sh`/`scripts/*.py` path; verified live the annotation appears for `bmad-preflight` and not for a working task.
  - `docs_station_cli.py`'s check-time PATH-environment dependency was undocumented — one docstring sentence added.
  - `pixi.toml`'s "Eighth leg" vs the memlog's "ninth leg" for the identical `docs-gen-test` addition — memlog corrected to match.
- **Deferred (1 entry, low, already tracked before this review pass):** `spec-pyforge-doctor/SPEC.md`'s `surface:` list doesn't yet list the six new script paths (SPEC.md hand-edits are hook-blocked; a full `bmad-spec` re-derivation is out of scope for this dispatch) — recorded in this spec's own `deferred:` frontmatter and promoted to `DW-FU-30-3` in the tracked ledger, citing the interim `scripts/spec_surface_allowlist.txt` fix.
- **Rejected — low (3 entries):** `docs-map-schema.json` lacks an `if`/`then` conditional for `kind: generated` requiring `generator:` (the runtime WARN already covers it; scope creep beyond this story). Inconsistent `owner:` values (`fleet`/`steward`/`doctor`) across the five sibling generated pages (no documented ownership rule to correct against; the field drives no behavior). `docs_currency.py` reports a generator crash with the same message as ordinary staleness (the finding's own `evidence["output"]` already carries the distinguishing detail; a clean fix needs a new exit-code convention across all 5 generators).
- **Rejected — false (5 entries):** an unguarded git subprocess call (git/repo/history absence is unreachable for a pixi task in this repo); a `"(top-level)"` pixi-feature mis-render (no top-level `[tasks]` table exists in this repo's `pixi.toml`); a `KeyError` risk on a `features`-less environment entry (verified: all 35 real environments declare `features`); a claim that the generator's identity should live under `sources:` (it correctly lives under its own `generator:` key, alongside `sources:`); and a claim that the station-duty-vs-script boundary was "resolved silently" (both alternatives were explicitly permitted; the diff consistently chose one of them).

**Follow-up review recommendation: `true`.** Two-or-more medium-verdict entries were patched in this first pass. The specific unverified risk: the staleness-stamp fix (stripping the stamp header before comparing in `write_generated_page`'s `--check` mode) changes the core staleness-detection semantics shared by all five generators, and both the fix and its regression test were authored by the same implementation agent that wrote the original bug, in the same pass — an independent adversarial re-check of that one fix (does stripping the header ever let a REAL content change slip through unnoticed, e.g. a change confined to whitespace immediately after the header) has not yet happened.

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 2410 passed, 1 skipped (twice: once pre-patch, once post-patch).
- `pixi run -e pyforge-guild docs-gen-test` — 47 passed post-patch (41 pre-patch + 6 new regression tests).
- `pixi run -e pyforge-guild detectors-ci` — exit 0, clean (post chain-currency + deferred-work reconcile).
- `python scripts/spec_surface_reconcile.py` — exit 0, "every tracked file governed or allowlisted; no drift" (via the interim allowlist entries, deferred item above).
- `python scripts/chain_currency_sweep_check.py` — exit 0, "all 8 station spine(s) current" (PRD/architecture-spine/epics `updated:` cascade for pyforge-doctor).
- Every `docs-*` generator run on an unchanged tree, twice, byte-identical (both content and stamp).
- Post-patch: every generator's `--check` reports `current` immediately after a fresh commit advances HEAD with no source change — the specific false-positive the review found is confirmed fixed.
- Live-confirmed all three user-visible bugs fixed: `skills-catalog.md` shows real descriptions for the 4 previously-blank skills; `station-cheat-sheet.md` shows a "not resolvable" note instead of a `marshal-mcp` traceback; `pixi-tasks.md` flags `bmad-preflight`'s missing script.
- I/O & Edge-Case Matrix audit: all 5 rows covered by a passing, actually-run test (idempotence: `test_render_is_deterministic`/`test_write_generated_page_writes_and_is_idempotent`/`test_head_stamp_is_idempotent_on_an_unchanged_tree`; pixi-task-added: `test_main_writes_then_check_agrees_then_a_pixi_toml_edit_reds_check`; CLI-verb-gained: `test_docs_station_cli.py::test_main_write_then_check_roundtrip`; SKILL.md-edited: `test_docs_skills_catalog.py::test_main_write_then_check_roundtrip`; hand-edit: `test_generated_page_stale_emits_warn` + live manual verification).

**Residual risks:** the follow-up-review risk named above (independent re-check of the stamp-stripping fix). `DW-FU-30-3` (SPEC.md surface not yet formally reconciled) remains open in the tracked ledger, not a residual risk of this pass's code. The three `owner:` inconsistencies and the schema's missing conditional are recorded as rejected-low in the triage log above, not carried as risk.


