---
title: 'Story 6.6: The chain verdicts come home'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '5dcb64299277e1c732f9344a634196543e58f64'
final_revision: '813464281bfb0b3a0417156290b3e23f8404adf6'
---

<intent-contract>

## Intent

**Problem:** `scripts/dream_chain_check.py`, `scripts/spec_surface_check.py` and
`scripts/deferred_work_check.py` all judge the artifact chain every station
shares (Dream→Spec links, tracked-file surface coverage, deferred-work
durability) but live outside Doctor — Charter §6 says Doctor must hold the
verdict. Stories 6.4/6.5 proved the port pattern for the ledger and the board;
this is the chain's turn.

**Approach:** Port all three scripts' read-only judgement logic into one new
`sources/chain.py`: `gather_dream_chain` (`Source.DREAM_CHAIN`),
`gather_spec_surface` (`Source.SPEC_SURFACE`), `gather_deferred_work`
(`Source.DEFERRED_WORK`), all `scope="repo"` per each original script's own
`DETECTOR` declaration. Add `PyYAML` as a real `pyforge-doctor` dependency —
the epic's own explicit departure from 6.4/6.5's hand-rolled-parser precedent.
Mechanism-only like 6.2-6.5: no `__main__.py` wiring, no `scripts/*_check.py`
deletion.

## Boundaries & Constraints

**Always:** No gather imports any `pyforge.<station>` package (independence
test mirrors board/ledger's AST scan). All three `Source` members register in
`sources.REGISTRY` with `subject_station="marshal"` — all three judge
Marshal-governed factory apparatus (`spec-regenerable-factory`/
`spec-surface-drift-reconciliation` are Marshal specs; the deferred-work
refile mechanism belongs to bmad-loop, Marshal's orchestrator), the same
station 6.4/6.5 used for their own Marshal-produced artifacts — and
`owning_station="doctor"`, `scope="repo"`, matching each original's own
`DETECTOR = {"scope": "repo"}` (preserved even for `deferred_work_check`'s
Tier-3 `implementation-artifacts/deferred-work.md` read, mirroring the
precedent Story 6.4 set keeping `STORY_STATUS` `scope="repo"` despite reading
`~/.bmad-loops`). `gather_dream_chain` ports all four invariants (INV-0
`spec-without-dream-link`, INV-1 `dream-without-spec`, INV-2
`owner-unassigned`/`spec-location-mismatch`, INV-3 `prd-not-sharded`/
`architecture-not-sharded`/`epics-missing`) with identical `kind`/message
text, using `yaml.safe_load` for frontmatter (already the original's own
parser). `gather_spec_surface` ports coverage (`ungoverned`,
`stale-allowlist`), drift (`drift`, `drift-blind`, `drift-presumed` as WARN
— non-gating, matching the original's own "informational" framing), and
`no-baseline`, restructured from the original's pre-formatted strings into
structured `{kind, path, detail}` dicts (there is no prior structured form to
preserve verbatim); its `git ls-files` call routes through
`cli_bridge.run_git`, degrading to WARN on `CliBridgeError` (never a second
subprocess site — AD-5). `gather_deferred_work` ports all four kinds
(`no-tracked-ledger`, `ledger-entry-unstatused`, `ledger-entry-unidentified`,
`tier3-only-deferral`) verbatim. Every gather degrades to WARN on
unreadable/missing/malformed input and never raises; per-project/per-station
isolation is structured in from the first draft — one try/except scoped to
the smallest unit body, accumulating into the caller's own list in place, no
shared outer catch-all — rather than rediscovered across review passes the
way 6.5 needed three to converge on the same lesson. `pyproject.toml` (the
`pyforge-doctor` package) gains `PyYAML` in `dependencies`; root `pixi.toml`'s
`[feature.pyforge-doctor.dependencies]` gains an explicit `pyyaml` conda pin
(this story's own Surface names `pixi.toml`) — a library add, never a feature
union. `data/report-schema.json`'s `finding.source` enum gains all three
values in lock-step with `models.py`. Each script gets its own test file
(`test_sources_chain_dream_chain.py`, `test_sources_chain_spec_surface.py`,
`test_sources_chain_deferred_work.py`) plus one
`test_sources_chain_independence.py`, mirroring board/ledger's naming; the
existing `test_sources_registry.py`/`test_models.py` set-equality tests need
no new file to keep covering the extended taxonomy.

**Block If:** nothing identified — all three scripts' logic is already
read-only and proven live in CI/pixi tasks; `subject_station` and `scope`
both settle by direct precedent (above).

**Never:** Add Playwright or any dependency beyond `PyYAML`. Touch
`scripts/dream_chain_check.py`, `scripts/spec_surface_check.py`,
`scripts/deferred_work_check.py`, their pixi tasks,
`.github/workflows/detectors.yml`, or `spec-regenerable-factory`'s/
`spec-surface-drift-reconciliation`'s `surface:` globs (Story 6.9's
retirement pass owns all of these). Port `spec_surface_check.py`'s
`--write-baseline` mutation path — the gather is read-only judgement only.
Wire any of the three into `__main__.py`/`doctor check`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open Spec undecomposed | status draft/ready/in-progress, no `owner-dream:` or no covering prose link | FAIL `spec-without-dream-link`/`dream-without-spec` | none |
| Dream owner mismatch | `owner: <station>` but Spec lives outside `pyforge-<station>` | FAIL `spec-location-mismatch` | none |
| Flat planning-artifacts | `prd.md`/`architecture.md` instead of sharded `prds/<run>/` | FAIL `prd-not-sharded` | none |
| Tracked file ungoverned | matches no spec `surface:` glob and no allowlist entry | FAIL `ungoverned` | none |
| Allowlist entry stale | pattern in `spec_surface_allowlist.txt` matches 0 files | FAIL `stale-allowlist` | none |
| Governed file drifted, no memlog | spec has a surface, no `.memlog.md` at all | FAIL `drift-blind` | none |
| Contract moved, didn't name the file | `.memlog.md` moved but doesn't mention the changed path | WARN `drift-presumed` (non-gating) | none |
| `git ls-files` unavailable | not a repo / git missing | WARN `spec-surface-unevaluable` | never raises |
| Tier-3-only deferred id | `DW-*` in `implementation-artifacts/deferred-work.md`, absent from the tracked ledger | FAIL `tier3-only-deferral` | none |
| Tracked ledger entry missing status | `## DW-*` heading, no `status:` line | FAIL `ledger-entry-unstatused` | none |
| Clean chain | dreams/specs/surface/ledger all consistent | one OK `Finding` per source | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add `Source.DREAM_CHAIN = "dream-chain"`, `Source.SPEC_SURFACE = "spec-surface"`, `Source.DEFERRED_WORK = "deferred-work"`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- add the three values to `$defs.finding.properties.source.enum`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- add three `SourceRegistration` rows (`subject_station="marshal"`, `owning_station="doctor"`, `scope="repo"`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- NEW. `gather_dream_chain(target)`, `gather_spec_surface(target)`, `gather_deferred_work(target)`; `yaml.safe_load` frontmatter parsing; `git ls-files` via `cli_bridge.run_git`.
- `src/shared/packages/pyforge-doctor/pyproject.toml` -- add `"PyYAML"` to `dependencies`.
- `pixi.toml` -- add a `pyyaml` conda pin to `[feature.pyforge-doctor.dependencies]`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` -- NEW.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` -- NEW.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- NEW.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_independence.py` -- NEW.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add the three `Source` members (closed-taxonomy-extended comment referencing Story 6.6/FR-15).
- [x] `data/report-schema.json` -- add `"dream-chain"`, `"spec-surface"`, `"deferred-work"` to the `source` enum.
- [x] `sources/__init__.py` -- add the three `SourceRegistration` rows to `REGISTRY`.
- [x] `pyproject.toml` + `pixi.toml` -- add the `PyYAML`/`pyyaml` dependency.
- [x] `sources/chain.py` -- new module: `gather_dream_chain(target)` porting INV-0..3 verbatim; `gather_spec_surface(target)` restructuring the original's printed findings into `{kind, path, detail}` dicts, `git ls-files` via `cli_bridge.run_git`; `gather_deferred_work(target)` porting all four kinds verbatim; per-project/per-station isolation built in from the start.
- [x] `tests/unit/test_sources_chain_dream_chain.py` -- cover the I/O matrix rows against real tmp fixtures, plus one mutation test per invariant.
- [x] `tests/unit/test_sources_chain_spec_surface.py` -- cover coverage/drift/blindness rows incl. the git-unavailable WARN path.
- [x] `tests/unit/test_sources_chain_deferred_work.py` -- cover the Tier-3/tracked-ledger I/O matrix rows.
- [x] `tests/unit/test_sources_chain_independence.py` -- port the independence test, `SOURCE` pointed at `sources/chain.py`.

**Acceptance Criteria:**
- Given a monorepo checkout, when `pyforge.doctor.sources.chain.gather_dream_chain`, `gather_spec_surface` and `gather_deferred_work` run, then each returns `Finding`s tagged with its own `Source`, routable through `verdict.exit_code_for` unchanged.
- Given `sources.REGISTRY`, when read, then it carries exactly one entry each for `DREAM_CHAIN`, `SPEC_SURFACE`, `DEFERRED_WORK`, all `subject_station="marshal"`/`owning_station="doctor"`/`scope="repo"`, and `test_every_source_member_has_exactly_one_registry_entry` passes.
- Given `sources/chain.py`, when AST-scanned, then it imports no `pyforge.<station>` package — enforced by the new independence test.
- Given each script's historical fixture input, when its ported invariant is exercised, then the finding's `kind`/message match the original script's output, and a mutation of that invariant's branch makes the corresponding test fail.
- Given one project/station with malformed input, when a gather runs across multiple projects/stations, then only that project/station's finding degrades to WARN — every other project/station's real FAIL/OK finding survives in the same run.
- Given `pyforge-doctor-test`, when run, then all prior tests plus the new ones pass, and `test_schema_source_enum_matches_the_source_taxonomy_exactly` passes.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 1, medium 2, low 2)
- defer: 1 (high 0, medium 1, low 0)
- reject: 8 (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: **`_collect_specs`/`_spec_entry` were not per-spec isolated**, contradicting the module's own docstring claim ("per-Spec isolation already lives in `_frontmatter`/`_satellite_titles`, which degrade rather than raise"). `_frontmatter` only degrades a block that fails to PARSE, not one that parses cleanly to the WRONG SHAPE — a `SPEC.md` with `owner-dream:` written as a YAML list (a plausible typo next to the legitimately-list-shaped `covers-dreams:`) raised `AttributeError` out of `_spec_entry`'s `.split("/")` call, escaping past `_check_dream_chain` into the outer `degrade_on_exception` and replacing EVERY dream/spec's real finding with one vacuous WARN. Reproduced live (an unrelated `orphan` Dream's real `dream-without-spec` FAIL vanished behind `dream-chain WARN | ... AttributeError: 'list' object has no attribute 'split'`). This is exactly the failure class this story's own Design Notes said to structure in from the first draft rather than rediscover a fourth time — it was missed for specs specifically (dreams and projects were already isolated). Fixed: `_collect_specs`/`_append_spec_entry` now wrap each spec's construction in its own try/except, appending a `dream-chain-unevaluable` WARN to the caller's shared `findings` list (threaded through `_check_dream_chain`) for that ONE spec only. Regression test added and mutation-confirmed (reverting the guard reproduces the exact live failure).
  - `[medium]` `[patch]` Edge Case Hunter: `_tracked_files` caught only `CliBridgeError`, not `UnicodeDecodeError` — `run_git` decodes with `text=True`, so a tracked path containing a non-UTF-8 byte raises straight past this function, unlike `sources/ledger.py`'s own `_git` wrapper, which already guards this exact exception class for the same underlying cause. Fixed: widened to `except (CliBridgeError, UnicodeDecodeError)`. Regression test added (monkeypatched `run_git` to raise) and mutation-confirmed.
  - `[medium]` `[patch]` Edge Case Hunter: `_check_spec_surface` re-fetched `git ls-files` internally via its own `_tracked_files(target)` call, despite its own docstring claiming "minus git ls-files (the caller already resolved that)" — `_gather_spec_surface` already fetched it once to decide the git-unavailable WARN path. A second, independent call could transiently fail after the first succeeded, and the `or []` fallback would silently coalesce that failure into "zero tracked files" (false-clean or spurious `ungoverned`/`stale-allowlist` findings) instead of surfacing the correct unevaluable WARN. Fixed: `_check_spec_surface` now takes `files` as a parameter instead of re-fetching. Regression test added (asserts `run_git` is called exactly once) and mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): `test_sources_chain_dream_chain.py`'s module docstring claimed `test_owner_unassigned_branch_mutation_is_caught` was "kept live as a directly-executable proof" — no such test exists anywhere in the file or the repo (confirmed by grep), and no comparable "kept live" mutation pattern exists anywhere else in this package (every sibling test file, e.g. `test_sources_board_chain_completeness.py`, uses the "verified during development, not re-encoded" convention with no such claim). Fixed: the false claim removed, docstring now matches the established, real convention verbatim.
  - `[low]` `[patch]` Blind Hunter: `pyproject.toml`'s new `"PyYAML"` dependency carried no version floor, unlike every sibling dependency in the same list (`jsonschema` derives one from the wheel; `mcp>=1.28.1` has an explicit floor) and unlike `pixi.toml`'s own `pyyaml = ">=6.0"` pin for the identical library. Fixed: `"PyYAML>=6.0"`, matching pixi.toml's pin.
  - `[medium]` `[defer]` Blind Hunter: `spec-pyforge-doctor`'s own `spec-surface` baseline has been drifting unreconciled since Story 6.2 (verified: 23 live `[drift]` findings against it today, including files added by 6.4/6.5, confirming this predates 6.6 and is not caused by it) — the spec's own `.memlog.md` anticipated this ("reconcile it as part of that epic") but no story's AC in the epic actually schedules running `--write-baseline --spec pyforge-doctor/spec-pyforge-doctor`. Logged to `deferred-work.md` (DW entry, this story's spec as source) rather than fixed here: reconciling 6.2-6.5's backlog alongside 6.6's own files is a repo-hygiene action spanning stories already merged, out of this story's Surface, and not blocking (the drift is a `[drift]` FAIL on `spec-pyforge-doctor`'s OWN separate spec-surface gate, not on anything this story's own AC or tests check).
  - `[low]` `[reject]` Blind Hunter: none of the three new sources are dispatched from `__main__.py`/`doctor check` yet. Explicitly spec-mandated (Boundaries: "Never: Wire any of the three into `__main__.py`/`doctor check`"), matching every prior 6.2-6.5 story's identical pattern — not a defect. The sub-point that the new `REGISTRY` rows carry no "why not dispatched" comment (unlike `CHECK_LAYOUT`'s row) is also not an inconsistency: `CHECK_LAYOUT` is the one outlier needing such a comment (a real budget conflict with a browser sweep); none of `STORY_STATUS`/`LEDGER_REGRESSION`/`CHAIN_COMPLETENESS`/`DASHBOARD_DRIFT`'s own rows carry one either.
  - `[low]` `[reject]` Blind Hunter: inline `import shutil`/`import hashlib` inside individual test functions diverges from sibling test files' module-scope-import style. Purely cosmetic, zero behavior impact, not worth churning working tests for.
  - `[low]` `[reject]` Blind Hunter: `_check_project_deferred_work` can append a real `no-tracked-ledger` FAIL and then still raise inside `_entries()` before returning, producing a mixed FAIL+WARN for one project. Verified this is not a masking bug: the FAIL is appended to the caller's list BEFORE the raise, so it survives; the WARN only ADDS information about a second, independent problem with the same project. Not reproduced live (requires a narrow permission-error trigger); the shape it describes is not actually incorrect.
  - `[low]` `[reject]` Blind Hunter: two different frontmatter-parsing philosophies (`yaml.safe_load` for Dreams/Specs, a hand-rolled parser for `SPEC.md`'s `surface:` block) coexist in one module. Explicitly spec-mandated and explained in the Boundaries section (dream_chain's original already used real YAML; spec_surface's hand-rolled parser is preserved deliberately, "preserve don't redesign," with its own documented historical bug-fix rationale) — not an oversight.
  - `[low]` `[reject]` Blind Hunter: `Finding.evidence` shape differs across the three new sources (`"subject"` vs `"path"` vs `"project"`/`"id"`). Same finding already `[reject]`ed twice in Story 6.5's own triage log for the identical concern across `CHAIN_COMPLETENESS`/`DASHBOARD_DRIFT`: `Finding.evidence` is documented as "Source-specific, opaque to this envelope," and each shape is verbatim from its own original script's own convention — unifying them would be an unauthorized redesign.
  - `[low]` `[reject]` Blind Hunter: INV-1 (`dream-without-spec`) and INV-2a (`owner-unassigned`) both fire for the same guild-owned, spec-less Dream. Verified this is inherited verbatim from the original `scripts/dream_chain_check.py`'s own `check()` — both loops are independent and unconditional there too, so a guild-owned Dream with no Spec double-fires in the ORIGINAL script as well. Faithful preservation, not a defect introduced by this port.
  - `[low]` `[reject]` Blind Hunter: `drift-presumed` findings are WARN, indistinguishable-by-status-alone from a genuine "could not evaluate" WARN. True of every WARN-vs-WARN distinction in this codebase (the `check`/`message` fields always carry the "why"), and the identical "OK-vs-WARN semantics" concern was already `[reject]`ed in Story 6.5's own triage log as "already open... wants one fleet-wide decision, not per-module drift" — not new to this story.
  - `[low]` `[reject]` Blind Hunter: `dream_chain`'s INV-3 and `deferred_work` both independently walk `_bmad-output/projects/*` with their own separate per-project isolation copies rather than a shared helper. A real DRY observation, not a correctness defect — the two units collect different fields per project, so a shared helper would need enough parameterization that the duplication is arguably cheaper for the two call sites that exist today.

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 1, medium 6, low 1)
- defer: 6 (high 0, medium 4, low 2)
- reject: 11 (high 0, medium 0, low 11)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): **a non-string Dream `title:` collapsed the ENTIRE gather** — the same "one unit's failure discards every other unit's finding" class the previous pass closed for Specs, still open for Dreams. `title:` with no value parses to YAML `null` and `title: 2026` to an `int`; both reach `_normalize_title`'s `.lower()` in `_check_dream_chain`'s satellite loop, which runs over already-collected in-memory data and therefore sits outside every per-unit try/except in the module. The `AttributeError` escaped to `degrade_on_exception` and replaced every real INV-0/1/2/3 FAIL with one vacuous WARN. Reproduced live by Blind Hunter (an unrelated `orphan` Dream's real `dream-without-spec` FAIL vanished; the loop only runs when some Spec carries a `## Satellite:` heading, and two live Specs do). Fixed at the collection BOUNDARY rather than the use site — `_collect_dreams` now coerces `owner`/`status`/`title` to `str`, which closes the class for every downstream consumer at once instead of guarding one `.lower()`. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Edge Case Hunter: a baseline entry that is valid JSON but **not an object** (a stray string/list/number from a hand-edit) reached `b.get("memlog")` in `_drift_findings` — the `AttributeError` escaped to `degrade_on_exception` and discarded every OTHER spec's already-computed coverage/drift finding. Inconsistent with the two guards already present in the same function (`isinstance(base, dict)` above it, `isinstance(b.get("files"), dict)` below it), so this was a gap in the port's own new defensive code, not inherited. Fixed: `if not isinstance(b, dict): b = None`, so a malformed entry means "no usable baseline for this spec" and falls through to the existing `no-baseline` finding. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter: `_parse_surface`'s broad `except Exception: return globs, excludes, drift` **silently un-governed** an unreadable SPEC.md. An empty surface is indistinguishable from "this spec governs nothing", so every file the spec really owned was reported FAIL `ungoverned` ("no spec surface and no allowlist entry") and every baselined one FAIL `drift … removed` — confidently wrong findings rather than an honest unevaluable, and a re-creation of the exact silent-governance-loss bug `scripts/spec_surface_check.py`'s own docstring records having fixed ("the checker reported the files as *removed* rather than erroring"). Reproduced by Blind Hunter: a 5-file fixture produced 10 confidently-wrong FAILs. Note this was NOT inherited — the original has an unguarded `read_text` that crashes loudly; the port converted a loud crash into a quiet lie. Fixed: `_parse_surface` raises; `_check_spec_surface` isolates per-spec into a `spec-surface-unevaluable` WARN naming the spec and suppresses the now-unsound COVERAGE half (coverage is a global computation over every surface) while every readable spec's own per-spec drift finding still lands. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter: `_load_allowlist` degraded a **present-but-unreadable** allowlist to `[]`, which is a lie with teeth — every allowlisted file is then reported FAIL `ungoverned`, whose message literally asserts "no allowlist entry", and every real entry silently becomes a `stale-allowlist` FAIL (13 patterns covering ~99 files in the live repo). Reproduced. Fixed by splitting the two failure modes the original never had to tell apart: ABSENT → `[]` (genuinely nothing exempted, the legitimate case for a library call against an arbitrary target), PRESENT-BUT-UNREADABLE → `None`, which the caller turns into the same `spec-surface-unevaluable` WARN + coverage suppression as an unreadable surface. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter: `gather_dream_chain` and `gather_deferred_work` emitted a **confident OK when their input trees simply did not exist** under `target` — "every Spec links a Dream, every Dream has a Spec" with `{"dreams": 0, "specs": 0}`, and "every Tier-3 deferral has a tracked twin" with `projects_scanned: 0`. A clean bill of health for a question never asked. The originals were anchored to their own `REPO_ROOT`; a library gather takes whatever it is handed, and `doctor check` defaults `path="."`, so running from any subdirectory produced this. Sibling `sources/ledger.py` sets the precedent of an honest WARN in the equivalent case. Fixed: both now return a `dream-chain-unevaluable`/`deferred-work-unevaluable` WARN when no input tree exists. The two tests that had encoded the old false-OK were rewritten — one to assert the WARN, one to assert the OK on a real-but-empty tree, so both halves of the distinction stay pinned. Mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter: `PyYAML` was added to `pyproject.toml` and the root `pixi.toml`, whose comment on the new line asserts "also a package run-dep" — but it was never added to `src/shared/packages/pyforge-doctor/pixi.toml`'s `[package.run-dependencies]`, the table the generated conda recipe's `run:` list is actually built from. The built `.conda` therefore did not depend on PyYAML, and `import pyforge.doctor.sources.chain` (module-scope `import yaml`) would raise `ModuleNotFoundError` on a standalone conda install. Same failure class as warden's own recorded `AUD-WARDEN-010`. Fixed: `pyyaml = ">=6.0"` added, matching both other declarations. (The identical pre-existing omission for `mcp`, from Story 2.1, is deferred rather than fixed — its two pins disagree and picking the authoritative one is not this pass's call.)
  - `[low]` `[patch]` Blind Hunter: four ported `surface-drift` branches had **zero test coverage** — the `sentinel:<path>` contract-hash mode, the `exempt` and zero-governed-files silence rules for `drift-blind`, and whether `surface-drift-exclude:` actually excludes anything (it appeared in the test file only as unasserted fixture scaffolding). The story's own AC requires a mutation of each ported branch to make a test fail, so these were an AC gap, not a nice-to-have. Fixed: four tests added, each mutation-confirmed. One of them (`test_spec_governing_no_files_is_not_drift_blind`) was found mutation-WEAK on first write and tightened — dropping the `governed.get(name)` condition makes the branch fire and then raise `KeyError`, which `degrade_on_exception` turns into a lone WARN, i.e. also a run containing no `drift-blind`; it now asserts the exact check set rather than an absence.

### 2026-08-09 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 2, medium 4, low 1)
- defer: 2 (high 0, medium 1, low 1)
- reject: 12 (high 0, medium 4, low 8)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: **`pixi.lock` was never regenerated after the two manifests gained PyYAML**, so the delivered dependency fix was inert. `pixi list --locked -e pyforge-doctor` failed with "lock file not up-to-date with the workspace", and the three `conda_source: pyforge-doctor[...]` records still declared `depends: [python, python, jsonschema]` — no `pyyaml`. This is CI-breaking, not cosmetic: `.github/workflows/dashboard.yml` installs with `locked: true` (its own comment records deliberately choosing `--locked` over `--frozen` so a stale lock fails loudly), so every dashboard run on this branch would have errored before reaching a task. The local env masked it by having pyyaml resolved already — it was in the doctor env at the BASELINE revision, pulled transitively, which is also why the root `pixi.toml` add produced no lock delta and the omission stayed invisible. Fixed: ran `pixi lock`; the diff is contained to exactly the intended change (43/40 lines — the three `pyforge-doctor` source records gain `pyyaml >=6.0` and rehash; no version moves anywhere else). `pixi list --locked -e pyforge-doctor` now succeeds. Correcting one detail of the report as filed: the finding attributed the env's pyyaml to `pyforge-warden`; the lock shows it explicitly present in the pyforge-doctor env on all three platforms both before and after — the real gap was only ever the package's own run-dependency record.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): **one unreadable `SPEC.md` suppressed EVERY unrelated file's coverage finding repo-wide**, and since the replacement is a non-gating WARN the run then reported exit 0 — a false green. This is a direct violation of the story's own AC ("only that project/station's finding degrades to WARN — every other project/station's real FAIL/OK finding survives in the same run"), introduced by the previous pass's own fix for the silent-un-governing bug: it correctly stopped lying about the dark spec, then took every other spec's answer down with it. Reproduced live by both lenses (a genuinely ungoverned file and a stale allowlist pattern both vanished behind one `chmod 000` SPEC.md). Fixed by splitting the two halves rather than suppressing both: `ungoverned` IS unsound under an unknown surface (the dark spec might own the file) and stays suppressed, but `stale-allowlist` is NOT — an unknown surface can only ever INFLATE a pattern's hit count, because the dark spec claims nothing and its files therefore fall THROUGH to the allowlist loop, so a pattern still at zero hits is still at zero with every surface known. False positives are impossible; only a missed one is. It now keeps gating. The remaining suppression is also no longer silent: a `spec-surface-unevaluable` finding names how many ungoverned candidates were withheld and why. Two regression tests added, both mutation-confirmed. NOT fixed: making the unevaluable finding itself gate (FAIL) — the spec's Boundaries mandate WARN for unreadable/malformed input, and "should WARN gate?" was already `[reject]`ed in Story 6.5's triage as wanting one fleet-wide decision.
  - `[high]` `[patch]` Edge Case Hunter: **`Path.glob` swallows `OSError` mid-traversal and yields nothing**, so every unreadable input directory read as an EMPTY one — and empty reads as clean. Reproduced live three ways: `chmod 000 docs/dreams/` turned a real `dream-without-spec` FAIL into `dream-chain ok`; `chmod 000 _bmad-output/projects/` turned three INV-3 FAILs into the same OK; and an unreadable `planning-artifacts/specs/` silently un-governed a spec's files, producing a spurious `ungoverned` FAIL with no warning — the exact silent-governance-loss defect `_parse_surface`'s own docstring exists to prevent, one directory level up and unguarded. Note the module already had the honest shape elsewhere: `_deferred_work_findings` uses `iterdir()`, which raises, and degrades correctly. Fixed by routing all five collection sites through a new `_listdir` helper (`sorted(d.iterdir())`, which raises), restructuring the two multi-level globs into per-project walks so a project's unreadable `specs/` isolates to a WARN naming THAT project instead of vanishing. `_collect_surfaces` was split out of `_check_spec_surface` in the process, which is also what makes the unknown-SURFACE vs unknown-EXEMPTIONS distinction above expressible. Three regression tests added, all mutation-confirmed.
  - `[medium]` `[patch]` Edge Case Hunter: a **PRESENT-but-unreadable governed file was reported FAIL `drift ... removed`** — a confidently wrong finding about a file that is still right there. `_sha1` degrades to `None` and `_spec_current_state`'s comprehension dropped those entries, which is correct for a file that is genuinely GONE (`removed` is then the true answer) but indistinguishable from one that merely cannot be read. Reproduced live. Fixed: a file that fails to hash but still `exists()` now raises, which the function's own per-spec try/except turns into a named `spec-surface-unevaluable` WARN; a genuinely absent file still drops out silently. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Edge Case Hunter: a **PRESENT-but-unreadable `.memlog.md` silently downgraded every gating `drift` FAIL to a non-gating `drift-presumed` WARN**, and the run then reported OK. `_contract_hash` collapsed the unhashable memlog to `""` — the ABSENT hash — so `spec_moved` was unconditionally True and, with `_memlog_text` degrading to `""` as well, nothing was ever "named" and everything landed in presumed. `drift-blind` does not catch it either, because the memlog IS `is_file()`. Reproduced live against real unreconciled drift. Fixed: present-but-unhashable raises (same `_unhashable` helper, same per-spec WARN isolation); the sentinel path got the identical treatment, since an unreadable sentinel was likewise being reported as `missing`. Regression test added and mutation-confirmed.
  - `[medium]` `[patch]` Edge Case Hunter: the same silent FAIL→WARN downgrade via a **baseline entry whose `memlog` key is missing or non-string**. The previous pass added `isinstance(base, dict)` and `isinstance(b.get("files"), dict)` guards but left `memlog`'s own shape unchecked, so a hand-edited entry in the tracked `.spec-surface-baseline.json` compared unequal to every real contract hash. The original indexed `b["memlog"]` and raised loudly. Reproduced live in two shapes (key absent; key set to `[]`). Fixed: `memlog` must be a `str` or the entry is unusable, falling through to the existing gating `no-baseline` finding — consistent with its two sibling guards. Regression test added and mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter: `_gather_dream_chain`'s unevaluable guard tested whether the two input DIRECTORIES exist, joined with `and`, so a present-but-empty `docs/dreams/` (or one holding only `README.md`) alongside no projects tree still produced the confident OK — asserting "every project uses the sharded planning tree" about zero projects. Reproduced. Fixed: the guard now tests what was actually COLLECTED (`not dreams and not specs and no projects tree`), which subsumes the original both-trees-missing case. Regression test added and mutation-confirmed.
  - `[medium]` `[defer]` Edge Case Hunter: `_parse_surface`'s hand-rolled reader recognises exactly one `surface:` spelling, so a quoted glob, a flow sequence, or any other indentation parses "successfully" to an EMPTY surface — silently un-governing the spec with no WARN, since nothing raised. Inherited verbatim from `scripts/spec_surface_check.py`; no live SPEC.md uses any of the three spellings. Logged to `deferred-work.md` as a NEW entry rather than patched, for the reason two existing entries already record: diverging in one of two live copies makes the repo-root detector and the Doctor port disagree on the same tree, so it belongs with Story 6.9's reconciliation.
  - `[low]` `[defer]` Blind Hunter: the existing ledger entry deferring `spec-pyforge-doctor`'s baseline drift concludes it "predates 6.6 and is not caused by it" — true of the inherited findings, but 9 of the 26 live `[drift]` findings are this story's OWN files (verified by cross-referencing the detector's output against `git diff --name-only`). The orchestrator owns that entry's status and text, so it was left untouched; a NEW entry records the correction so whoever picks it up does not act on the premise that 6.6 contributed nothing. The deferral decision itself is unchanged.
  - `[medium]` `[reject]` Blind Hunter: `drift-presumed` emits one finding per path where the original SUMMARISES per spec, with a recorded rationale (995 entries would bury the gating findings). Rejected: the port emits strictly MORE information than the original, not less, and the spec's own Design Notes mandate the per-item `{kind, path, detail}` structure precisely because the original's output was pre-formatted console strings. Volume-vs-rendering is a reporter concern owned by whatever wires these gathers behind a CLI — the same "wants one fleet-wide decision, not per-module drift" reasoning that closed the adjacent WARN-semantics point in Story 6.5's triage.
  - `[medium]` `[reject]` Blind Hunter: `gather_deferred_work` can never find anything in CI, because every input it reads is gitignored Tier-3 scratch — yet it reports a confident OK. Rejected: with zero Tier-3 deferrals, "every Tier-3 deferral has a tracked twin" is genuinely true, not vacuous — this is not the "question never asked" shape the previous pass fixed (that one claimed an answer with no input TREE at all, and its guard is still in place). The original script behaves identically, and the spec's Boundaries explicitly preserve `scope="repo"` for this exact Tier-3 read by direct precedent from Story 6.4.
  - `[medium]` `[reject]` Edge Case Hunter: `gather_spec_surface` has no "target is not a monorepo root" guard, unlike its two siblings, so a run from a subdirectory reports every file in that subtree FAIL `ungoverned`. Rejected after implementing it and reverting: the two cases are not symmetric. The sibling guards replace a false OK — a SILENT wrong answer — whereas one here replaces a loud, self-evident wrong answer with a WARN that ALSO silences the legitimate "this repo governs nothing yet" FAIL an unconfigured root should report, since an empty repo and a subdirectory are indistinguishable from the filesystem alone. Two existing tests deliberately pin the loud shape with that rationale written out. Trading a loud wrong answer for a quiet one is the defect class this whole pass is closing. A `git rev-parse --show-toplevel` probe would discriminate properly but adds a second git call against the module's own AD-5 single-site rule — a design call, not a review patch. Already recorded in the ledger by a prior pass; a code comment now records why it is deliberate.
  - `[medium]` `[reject]` Blind Hunter: no test guards the port against the originals, though both stay live until Story 6.9, so the AC's "matches the original script's output" is asserted rather than proven. Rejected, but recorded: BOTH reviewers independently built differential harnesses for exactly this and found **zero behavioural divergences** — 39 synthetic cases (13 dream-chain, 12 deferred-work, 14 spec-surface against real `git init` repos) plus the live repo. Re-verified after this pass's patches: the three gathers return 1 OK / 26 `drift` / 2 `tier3-only-deferral`, byte-identical to the three original scripts' own live output (26 and 2 confirmed by direct execution). A subprocess golden test would be born to die — Story 6.9 deletes the scripts it would compare against.
  - `[low]` `[reject]` Blind Hunter: the allowlist's `reason` is parsed, threaded through `_load_allowlist` → `allow` → `allow_res`, and then discarded, dropping the original's "no silent exemptions" printout. Rejected: the actionable half is already ported (`stale-allowlist` names every pattern matching nothing), and rendering the exemption table is a reporter concern for the CLI story; the parse stays verbatim so the reason survives for it.
  - `[low]` `[reject]` Edge Case Hunter: `git ls-files` C-quotes non-ASCII paths. Real and reproduced, but already recorded in `deferred-work.md` by an earlier pass with the same inherited-defect reasoning — not re-appended (the orchestrator owns that entry).
  - `[low]` `[reject]` Edge Case Hunter: `surface-drift: sentinel:<path>` is joined with `target /`, so an absolute or `../` value reads outside the target. Rejected: the value comes from a tracked, reviewed SPEC.md, which is not a trust boundary, and the effect is a read-only hash that only decides whether a drift finding fires. Inherited.
  - `[low]` `[reject]` Edge Case Hunter: a `**`-heavy `surface:` glob backtracks catastrophically (95s on one path, unbounded by the 5s NFR-4 budget). Rejected: requires an erroneous or hostile glob in a tracked SPEC.md, which would itself be the defect; inherited verbatim from the original's `_glob_to_re`.
  - `[low]` `[reject]` Edge Case Hunter: `_check_project_sharded`/`_check_project_deferred_work` can append partial real findings AND an unevaluable WARN for the same unit, unlike `_append_spec_entry`'s "never both and never neither". Rejected: no finding is lost — the WARN only adds information about a second problem with the same unit. Same shape already `[reject]`ed in this spec's first pass.
  - `[low]` `[reject]` Blind Hunter: `evidence["status"]` means four different things across `gather_dream_chain`'s own kinds. Rejected: `Finding.evidence` is documented "Source-specific, opaque to this envelope", the shape is verbatim from the original's own print column, and the adjacent evidence-shape concern was already `[reject]`ed twice in Story 6.5 and once in this spec's first pass.
  - `[low]` `[reject]` Blind Hunter: dead plumbing (`_spec_entry`'s unread `"path"`, `specs[name]["globs"]`) and ruff findings (`RUF022`, `FURB167`, `I001`) in the new files. Rejected: both dict keys are verbatim from the originals' collected shape, and the package has no lint task — sibling `board.py` carries the same ruff findings, so fixing only `chain.py` would create the inconsistency it claims to remove.
  - `[low]` `[reject]` Blind Hunter: ~30% of `chain.py` is prose, with several docstrings longer than the functions they describe. Rejected: this module's docstrings deliberately carry the per-branch rationale and the review history that produced it, which is the established convention across `sources/board.py` and `sources/ledger.py`.

### 2026-08-09 — Review pass (follow-up 3)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 4, medium 5, low 4)
- defer: 2 (high 0, medium 1, low 1)
- reject: 9 (high 0, medium 2, low 7)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: **one unreadable governed file blanked its spec's ENTIRE drift verdict** — the previous pass's own fix, over-corrected. `_spec_current_state`'s per-SPEC try/except wrapped the whole governed-file loop, so `_unhashable`'s raise for ONE file discarded every OTHER file's already-computed drift finding for that spec and replaced the lot with a single non-gating WARN — a red run reporting exit 0. Reproduced live: three genuinely-drifted governed files, `chmod 000` on one, **3 gating `drift` FAILs → 1 WARN**. The prior pass's own regression test could not see it (one-file surface). Fixed by splitting the two nested units the function actually has: per-SPEC isolation stays for the CONTRACT hash (an unreadable memlog/sentinel genuinely makes the whole spec unmeasurable, since every file compares against that one hash), and per-FILE isolation is added for the governed files (one unreadable file makes exactly ONE comparison unsound). The unhashable path is returned in a new `skipped` set and dropped from BOTH sides of the baseline diff — omitting it from `files` alone would have re-created the `drift ... removed` lie the branch exists to prevent. Regression test added and mutation-confirmed.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): **a tracked symlink-to-a-DIRECTORY inside a governed surface took that spec permanently dark.** The port probes `(target / f).exists()`, which FOLLOWS the link and answers True, while `_sha1` returns None (`IsADirectoryError`) — so `_unhashable` fired on a path that is present, readable, and simply not a regular file. The original guarded this exact case with `(REPO_ROOT / f).is_file()` (`spec_surface_check.py:249`); the port dropped the guard. Reproduced in a real git fixture, and **this repo tracks exactly one such path today** — `.claude/skills/cf-atlas-legacy/active -> 8.78.0` (`git ls-files -s` mode `120000`; `exists()` True, `is_file()` False) — currently allowlisted, so it is one surface-widening away from silencing a spec's drift permanently rather than transiently. Fixed: restored `is_file()` (via the raising `_is_file` below). Regression test added and mutation-confirmed.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): **an unreadable input DIRECTORY collapsed every unrelated unit's real finding into one vacuous WARN** — the story's own AC inverted. `_collect_dreams`, `_collect_specs`'s governance loop, `_sharded_findings` and `_collect_surfaces` all called `_listdir` (correctly raising) with no per-unit isolation, so the `PermissionError` escaped to the outer `degrade_on_exception`. Reproduced live: `chmod 000 docs/dreams/` turned **4 real FAILs — including three INV-3 findings that never read `docs/dreams/` at all — into 1 WARN**; `chmod 000 docs/governance/` did the same. Fixed: each collection root now isolates into a `dream-chain-unevaluable`/`spec-surface-unevaluable` WARN naming the tree that went dark, via a new `_unreadable_input` helper, while every other unit's finding survives. Two regression tests added, both mutation-confirmed.
  - `[high]` `[patch]` Edge Case Hunter: **`Path.is_dir()`/`Path.is_file()` swallow `OSError` and answer `False`, so an unreadable ANCESTOR read as "absent" — and absent reads as clean.** The previous pass introduced `_listdir` to close exactly this class for LISTING a directory, and left it wide open for the EXISTENCE PROBES that decide whether to list. Reproduced live, four ways: `chmod 000 docs/` (the PARENT of `docs/dreams/`) silently zeroed every Dream and a real `dream-without-spec` FAIL vanished with **no WARN at all**; `chmod 000` on a project's `implementation-artifacts/` turned **2 real deferred-work FAILs into a confident `ok deferred-work`**; `chmod 000 planning-artifacts/` made `gather_deferred_work` assert "the WHOLE record is gitignored" about a project whose tracked ledger is right there, and re-flag its already-promoted `DW-1`; and an unreadable `spec-<slug>/` or `planning-artifacts/` silently un-governed a spec, producing spurious `ungoverned` FAILs (or, when the files are allowlisted, a confident OK) with nothing naming the cause — the exact silent-governance-loss defect `_parse_surface`'s own docstring exists to prevent, one and two directory levels up. Fixed with a `_probe`/`_is_dir`/`_is_file` trio that raises on an undeterminable answer and returns `None`/`False` only for genuine absence, routed through all eleven load-bearing probe sites; each existing per-unit try/except turns the raise into a named WARN. Six regression tests added, all mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter: the **independence guard that is this module's entire reason for existing had a hole**: `_imported_modules` did `if node.level: continue`, commented "relative: ..models etc, never a station". From `pyforge/doctor/sources/`, level 3 IS the `pyforge` namespace — verified exploitable by inserting `from ...marshal import policy` into `chain.py`, after which **all five of that file's tests passed**. The companion textual test cannot catch it either: a relative import produces no `pyforge.marshal` string constant. Fixed: `_resolve_relative` resolves relative imports against the module's own package instead of waiving them, with a live regression test pinning it; `doctor` was made an explicit exclusion in the sibling-station tuple (it is the OWNING station, and `..models`/`..cli_bridge` are exactly the permitted dependencies — an exclusion that could stay implicit only while relatives were waived wholesale). Mutation-confirmed. A ledger entry already recorded this as wanting a fleet-wide fix; a NEW entry records that chain's copy is now closed and only the ledger/board siblings remain.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter: **nine ported branches had no mutation-killing test**, which this story's own AC requires ("a mutation of that invariant's branch makes the corresponding test fail"). Both lenses built independent mutation harnesses and agreed on the set. Tests added for: `_parse_surface`'s comment/blank-line-inside-a-block-sequence rule (the single most load-bearing line in the port — the original's own docstring records it as a real historical silent-un-governing bug); `_glob_to_re`'s documented dialect (`**` spans `/`, `*`/`?` do not); INV-1's slug fallback; the `docs/governance/spec-*/SPEC.md` discovery loop and `_expected_spec_dir`'s guild branch (both had ZERO real coverage — the two existing guild tests write to `_bmad-output/projects/docs/governance/…`, a path the gather never walks, and assert an ABSENCE that a never-collected Spec satisfies trivially); `_entries`' per-entry slice boundary; `_anonymous`'s heading-reset and positional `field_taken` rules; `_ids`' trailing-hyphen strip; the drift `added`/`removed` labels; multi-owner governed append; `_frontmatter`'s `---` fence guard; `_normalize_title`'s punctuation strip; `_collect_surfaces`' `spec-` prefix filter; and `_contract_hash`'s `+missing` sentinel branch.
  - `[low]` `[patch]` Blind Hunter: `str(ALLOWLIST_REL)` rendered a finding's `path` with OS-native separators (`scripts\spec_surface_allowlist.txt` on Windows, and `pixi.lock` carries win-64 for this env) while every other `path` in the source is a forward-slash `git ls-files` value. Fixed: `.as_posix()`.
  - `[low]` `[patch]` Edge Case Hunter: two projects with unreadable `specs/` directories produced WARNs whose `evidence["subject"]` was both the literal string `"specs"` — every project's specs dir has that name, so a machine consumer could not tell them apart. Fixed: `subject` is the PROJECT. Mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter: `SPEC_GLOB` was dead in production (`_collect_surfaces` deliberately abandoned it for `_listdir`) but the test helper `_specs_and_governed` still rebuilt the spec dict through it — a parallel discovery implementation that would silently disagree with production the moment the real rules changed, while writing the "real" baselines four drift tests depend on. Fixed: the helper calls `chain._collect_surfaces`; the dead constant is deleted and its rationale folded into the docstring that referenced it.
  - `[low]` `[patch]` Blind Hunter: `_collect_dreams`' docstring claimed the function was "verbatim from the original" while its `str()` coercion silently changes values the original preserved (PyYAML resolves an unquoted `owner: no` to `False`, rendered `""` here). Fixed: the docstring now records the coercion as a deliberate, documented divergence.
  - `[medium]` `[defer]` Blind Hunter: `score._is_gather_failure` is hardcoded to `check == "doctor.sources.atlas" and not finding.evidence`, so a wholly-failed chain gather grades its axis **C** rather than `INCOMPLETE`. Reproduced directly (`score.grade()` on the `degrade_on_exception` WARN returns overall `C`). Latent — this story wires nothing into `doctor check`, so nothing feeds these findings to `score.grade()` yet — and the same gap applies to `board.py`/`ledger.py`, so the fix is one generalisation of the predicate, not a per-module patch. Logged as a NEW ledger entry.
  - `[low]` `[defer]` Blind Hunter: status correction appended for the existing relative-import ledger entry (existing entries left untouched — the orchestrator owns them): its "fixing chain alone leaves two of three holed" premise is overtaken now that chain's copy is fixed.
  - `[medium]` `[reject]` Blind Hunter: `degrade_on_exception` is passed the same `check` string as the clean-OK finding, so "the whole gather blew up" and "everything is fine" differ only by `status`. Real, but `sources/board.py` passes `"chain-completeness"`/`"dashboard-drift"` in exactly the same shape — this is a fleet-wide convention, not drift introduced here, and the identical "wants one fleet-wide decision, not per-module drift" reasoning already closed the adjacent WARN-semantics point twice. Note it is also NOT what would fix the `score.grade()` deferral above: `_is_gather_failure` names atlas specifically, so renaming the label alone changes nothing.
  - `[medium]` `[reject]` Blind Hunter: `drift-presumed`'s one-finding-per-file volume can dominate `score._axis_grade` (995 WARNs against 26 FAILs → D instead of F). Already `[reject]`ed in the previous pass as a reporter concern; the new grading evidence does not change it, because the same "not wired into any CLI" fact that makes the `score` finding a DEFER makes this one moot, and the per-item `{kind, path, detail}` structure is spec-mandated.
  - `[low]` `[reject]` ×7: seven findings that are already recorded verbatim in `deferred-work.md` by earlier passes and are the orchestrator's to own — the `spec-pyforge-doctor` baseline drift (two entries, including this pass's own correction), the `git ls-files` C-quoting of non-ASCII paths, the scalar-`covers-dreams` character iteration, `_parse_surface`'s single recognised `surface:` spelling, the absent "target is not a monorepo root" guard in `gather_spec_surface`, and the load-sensitive `test_check_speed_budget` flake. The last was re-verified rather than assumed: it fails **more often at the BASELINE revision than with this pass's changes** (4/5 vs 2/5 across 10 runs), and `sources/chain.py` is never imported during the measured run, so it is environmental and structurally unrelated. Re-appending any of these would duplicate an entry the orchestrator already owns.

## Design Notes

`gather_spec_surface` is the one detector needing real structuring work
rather than a byte-verbatim port: the original's findings are pre-formatted
strings (`f"[ungoverned] {f}: ..."`), not dicts, so this gather derives its
own `{kind, path, detail}` shape from the same comparison logic rather than
parsing the original's print statements. `--write-baseline`'s mutation has no
home here — a future story wiring a CLI onto `sources.REGISTRY` gathers is
where that capability, if still needed, would resurface.

Stories 6.4 and 6.5 each needed three-plus review passes to converge on one
recurring lesson: a per-project/per-station try/except added AFTER an outer
catch-all still lets one bad input mask every other project's real finding,
because some nested access always sits outside the inner guard. `chain.py`'s
three gathers should structure their per-unit loops this way from the first
draft — try/except scoped to the smallest possible body, findings
accumulated into the caller's own list in place — rather than rediscovering
it here a fourth time.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: all pass (current count + new).
- `python -c "from pyforge.doctor.sources import chain; from pathlib import Path; r=Path('.'); print(chain.gather_dream_chain(r)); print(chain.gather_spec_surface(r)); print(chain.gather_deferred_work(r))"` (from the monorepo root) -- expected: no traceback, well-formed `Finding` tuples.

**NOTE on running the suite from a bmad-loop worktree** (same caveat Stories 6.4/6.5
recorded): point `PYTHONPATH` at this worktree's own `pyforge-doctor/src` and the
env's interpreter explicitly, or the task silently tests `main`'s sources instead
of the branch's.



## Auto Run Result

Status: done (follow-up review pass 3 — review-driven changes only; no re-implementation)

**Summary of implemented change.** This pass made no feature change. It closed one
coherent defect class the three prior passes had each narrowed but not eliminated:
**a degraded read producing a confident answer.** Six distinct live reproductions,
all in the new port and none inherited (the originals crash loudly where the port
now lied quietly), plus one over-correction introduced by the previous pass's own
fix. Alongside them, nine ported branches that no test killed under mutation —
an explicit AC gap, not a nice-to-have — were given tests.

**Files changed** (this pass; the dependency manifests and `pixi.lock` were NOT
touched — no new dependency was added, `os` and `stat` are stdlib):
- `src/.../doctor/sources/chain.py` — added the `_probe`/`_is_dir`/`_is_file` trio
  (probes that raise rather than answer "absent" for an undeterminable case) and
  routed all eleven load-bearing probe sites through it; isolated the four
  unguarded `_listdir` collection roots behind a new `_unreadable_input` WARN;
  split `_spec_current_state`'s single per-spec guard into per-SPEC (contract
  hash) + per-FILE (governed files) isolation, returning a `skipped` set that
  `_drift_findings` now excludes from both sides of the baseline diff; restored
  the original's `is_file()` gate for non-regular governed paths; `subject` on the
  unreadable-specs-dir WARN is the project, not the literal `"specs"`;
  `ALLOWLIST_REL.as_posix()`; deleted the dead `SPEC_GLOB`.
- `tests/unit/test_sources_chain_dream_chain.py` — +8 tests.
- `tests/unit/test_sources_chain_spec_surface.py` — +10 tests; `_specs_and_governed`
  now calls production's own `_collect_surfaces` instead of a parallel glob.
- `tests/unit/test_sources_chain_deferred_work.py` — +6 tests.
- `tests/unit/test_sources_chain_independence.py` — +1 test; relative imports are
  resolved against the module's package instead of waived.

**Review findings breakdown.** 13 patched (4 high, 5 medium, 4 low), 2 deferred
(1 medium, 1 low), 9 rejected (2 medium, 7 low — seven of them already recorded in
`deferred-work.md` by earlier passes, left to the orchestrator rather than
duplicated). Both lenses independently reported the symlink and unreadable-directory
classes; the over-suppression regression came from Blind Hunter alone.

**Verification performed.**
- Full suite: **705 passed, 1 skipped** (682 before this pass — +25 tests), with the
  single pre-existing `test_check_speed_budget` flake excluded. That flake was
  re-verified rather than assumed: at the BASELINE revision's package source it
  fails 4/5 runs, versus 2/5 with this pass's changes, and `sources/chain.py` is
  never imported during the measured run (nothing wires it into `__main__.py`).
- Chain tests alone: 100 passed.
- **Mutation sweep: 26 single-branch mutations, 26 killed, 0 survivors** — every
  ported branch this pass added a test for, plus every fix it made. The harness
  asserts it imports the mutated copy (an earlier run silently tested the installed
  package and reported 25 false survivors).
- **Live port fidelity re-confirmed against the originals**, unchanged by this pass:
  `dream_chain` OK (original exits 0), `spec_surface` 26 `drift` / 0 presumed
  (original `--json`: `findings` 26, `drift_presumed` 0), `deferred_work` 2
  `tier3-only-deferral` (original prints 2).
- Each of the eight reproductions re-run against the patched module: all now yield
  an honest WARN naming what went dark, with every unrelated FAIL surviving.

**Residual risks.**
- The `_probe` trio changes behaviour only for undeterminable reads; a genuinely
  absent path still answers "absent" exactly as before, and the live differential
  above shows no change on real data. Unreadable inputs are rare in CI, so these
  paths will mostly be exercised by their own tests.
- `gather_spec_surface` still reports loudly (not as a WARN) when handed a
  subdirectory rather than a monorepo root — deliberate, already in the ledger.
- A wholly-failed chain axis still grades `C` rather than `INCOMPLETE` downstream;
  latent until a story wires these gathers into `doctor check`, and deferred.
