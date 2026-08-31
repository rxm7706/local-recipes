---
title: 'Story 6.4: The ledger verdicts come home'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 'f9fc4cbf283957c3c2fbcb050ed9e18599aecc61'
final_revision: 'ddf19fa7b179f20c5aa09f8b28ae88a14d24b124'
---

<intent-contract>

## Intent

**Problem:** `scripts/ledger_regression_check.py` and `scripts/story_status_check.py`
both judge an artifact Marshal produces (the tracked sprint ledger, and the
Tier-3 sprint-status feed Marshal's promotion pipeline reads) but live outside
Doctor — the one station Charter §6 says must hold the verdict. Doctor already
proved the pattern once for `marshal-durability` (Epic 5); these two are next.

**Approach:** Port each script's read-only judgement logic into a new Doctor
`gather()` — `ledger_regression` into a new `sources/ledger.py`
(`Source.LEDGER_REGRESSION`), `story_status` into the existing
`sources/marshal.py` beside `MARSHAL_DURABILITY`'s own `gather`
(`Source.STORY_STATUS`) — each producing `Finding`s through Doctor's own
contract, registered in `sources.REGISTRY`. Mechanism-only, like Stories
6.2/6.3: no `__main__.py` CLI wiring, no `scripts/*_check.py` deletion (Story
6.9's job) — the verdict moving into Doctor's package is the whole point,
reachability via a verb is a separate, later concern.

## Boundaries & Constraints

**Always:** Neither new module imports `pyforge.marshal` (or any other
station package) — read only tracked git history (`cli_bridge.run_git`, the
sole subprocess site, AD-5) and, for `story_status`, local filesystem state
(`~/.bmad-loops/pyforge-<slug>/.bmad-loop/runs/*/state.json`, plain
`pathlib`/`json`, no subprocess). Both gathers degrade to a WARN/OK Finding on
any unreadable/missing input, never raise. `data/report-schema.json`'s
`finding.source` enum gains both new values — `test_schema_source_enum_
matches_the_source_taxonomy_exactly` fails otherwise (precedented: Story 5.1
shipped `MARSHAL_DURABILITY` without this and it went undetected for a day).
Both new `Source` members register in `sources.REGISTRY` with
`subject_station="marshal"`, `owning_station="doctor"`, `scope="repo"`
(matching each script's own current `DETECTOR` declaration — reclassifying
`story_status`'s scope, despite it touching `~/.bmad-loops`, is out of this
story's surface; preserve, don't redesign). Marshal's existing pre-write
guards (`promote_sprint_status.py`, `--project` scoping) are untouched.

**Block If:** nothing identified — both scripts' logic is fully read-only and
already proven live in CI/pixi tasks.

**Never:** touch `scripts/ledger_regression_check.py`, `scripts/story_status_
check.py`, `scripts/detectors.py`, `pixi.toml`'s existing detector tasks, or
`.github/workflows/detectors.yml` (retiring the scripts is Story 6.9). Wire
either new source into `__main__.py`/`doctor check` (no story in this epic's
Surface list does — verified against 6.5/6.6). Add a PyYAML dependency (both
scripts already use a hand-rolled tiny parser for the same reason the
existing `marshal.py` does). Change `MARSHAL_DURABILITY`'s own existing
`gather()` behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean revision range | ledger unchanged `done` keys between base/head | one OK `Finding`, `Source.LEDGER_REGRESSION` | none |
| Regression | a `done` key reads non-terminal at head | FAIL `Finding`(s), `check="done-key-regressed"` | none — reported, not raised |
| Renamed-but-still-done | id prefix changes, kebab tail survives as `done` | no regression (continuity) | none |
| Ledger deleted holding `done` keys | ledger path absent at head | FAIL `Finding`, `check="ledger-deleted"` | none |
| Base ref unresolvable | e.g. no `origin/main` | one WARN `Finding` | never raises |
| base == head, no parent | same commit, no parent | one WARN `Finding` | never raises |
| False-green story | feed reads `done`, harness says `deferred`/`escalated`/`abandoned`, no commit/merge/subject evidence | FAIL `Finding`, `Source.STORY_STATUS` | none |
| Hand-landed story | no run record at all | silent — no `Finding` | none |
| No Tier-3 feeds present | `_bmad-output/projects/*/implementation-artifacts/` absent/empty | one OK `Finding`, `evidence={"audited": 0}` | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add `Source.LEDGER_REGRESSION = "ledger-regression"` and `Source.STORY_STATUS = "story-status"`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- add both new values to `$defs.finding.properties.source.enum`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- add two `SourceRegistration` rows (`LEDGER_REGRESSION`, `STORY_STATUS`; `scope="repo"`, `subject_station="marshal"`, `owning_station="doctor"`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` -- NEW. Port `scripts/ledger_regression_check.py`'s `check(base, head)` into `gather(target, *, base="origin/main", head="HEAD") -> tuple[Finding, ...]`, via `cli_bridge.run_git`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` -- add `gather_story_status(target, *, loop_root=None) -> tuple[Finding, ...]`, porting `scripts/story_status_check.py`'s logic; extend `__all__`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py` -- NEW unit tests for `sources.ledger.gather` (I/O matrix rows), using real tmp git repos.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_independence.py` -- NEW, mirrors `test_sources_marshal_independence.py` for `sources/ledger.py`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` -- NEW unit tests for `gather_story_status` (I/O matrix rows).

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add the two `Source` members (append after `ADOPTION`, closed-taxonomy-extended comment referencing Story 6.4/FR-15).
- [x] `data/report-schema.json` -- add `"ledger-regression"`, `"story-status"` to the `source` enum.
- [x] `sources/__init__.py` -- add both `SourceRegistration` rows to `REGISTRY`.
- [x] `sources/ledger.py` -- new module: `_git` wrapper (via `cli_bridge.run_git`/`CliBridgeError`, mirrors `marshal.py`'s own), tiny `_parse_statuses`, `_tail`/`_ID_PREFIX_RE`, `_ledger_paths(target, rev)` (via `git ls-tree`), `_check(target, base, head) -> list[dict]`, `gather(target, *, base="origin/main", head="HEAD")` mapping each finding dict to a `Finding(source=Source.LEDGER_REGRESSION, ...)`, preserving the original script's same-commit/no-parent fallback and unresolvable-base WARN.
- [x] `sources/marshal.py` -- add `_harness_tasks(loop_root, slug)` (reads `~/.bmad-loops` run state via plain `pathlib`/`json`), `gather_story_status(target, *, loop_root=None)` porting the false-green detection (commit_sha / merge-commit / main-subject evidence, `NOT_LANDED` phases), one `Finding` per false-green key plus one OK summary `Finding` when none found.
- [x] `tests/unit/test_sources_ledger.py` -- cover every I/O matrix row for `ledger.gather` against real tmp git repos (init, commit ledgers under `_bmad-output/projects/<p>/planning-artifacts/sprint-status-ledger.yaml`, branch literally named `origin/main` to make `base` resolvable without a real remote).
- [x] `tests/unit/test_sources_ledger_independence.py` -- port `test_sources_marshal_independence.py`'s three tests, `SOURCE` pointed at `sources/ledger.py`.
- [x] `tests/unit/test_sources_marshal_story_status.py` -- cover the false-green / hand-landed / no-feeds I/O matrix rows for `gather_story_status`, with `loop_root` and `target` both pointed at `tmp_path` fixtures (no real `~/.bmad-loops` or real git history dependency).

**Acceptance Criteria:**
- Given a monorepo checkout, when `pyforge.doctor.sources.ledger.gather` and `pyforge.doctor.sources.marshal.gather_story_status` run, then each returns `Finding`s tagged `Source.LEDGER_REGRESSION`/`Source.STORY_STATUS` respectively, routable through `verdict.exit_code_for` unchanged.
- Given `sources.REGISTRY`, when read, then it carries exactly one entry each for `LEDGER_REGRESSION` and `STORY_STATUS`, both `subject_station="marshal"`/`owning_station="doctor"`/`scope="repo"`, and `test_every_source_member_has_exactly_one_registry_entry` passes.
- Given `sources/ledger.py` and `sources/marshal.py`, when AST-scanned, then neither imports `pyforge.marshal` (or any other station package) — enforced by the existing/new independence tests.
- Given `pyforge-doctor-test`, when run, then all prior tests plus the new ones pass, and `test_schema_source_enum_matches_the_source_taxonomy_exactly` passes.

## Spec Change Log

(none — no `bad_spec`/`intent_gap` findings this pass)

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 0, medium 3, low 8)
- defer: 9 (high 0, medium 3, low 6)
- reject: 1 (low 1)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `sources/__init__.py`'s two doc comments ("today's 9"/"All nine") went stale the moment this diff appended 2 registry rows without updating the surrounding prose. Fixed: reworded both to state 11 and to name Story 6.4's own two additions.
  - `[low]` `[patch]` Blind Hunter: `sources/__init__.py:137`'s blanket "(none reads host/tmux state yet...)" comment is now false and directly contradicted by `STORY_STATUS`'s own adjacent registration comment (this diff's `gather_story_status` reads `~/.bmad-loops`). Fixed: reworded to clarify `scope="repo"` means "declares itself CI-safe," not "never reads host state," and pointed at the `STORY_STATUS` row's own rationale.
  - `[low]` `[patch]` Blind Hunter: `gather_story_status`'s two new `git log` calls silently inherited `cli_bridge.run_git`'s 30s default instead of matching `scripts/story_status_check.py`'s own `sh()` helper's `timeout=60`. Fixed: added an optional `timeout` kwarg to `sources/marshal.py`'s `_git` wrapper (default unchanged at 30s, so every existing call site — including the untouched `MARSHAL_DURABILITY` `gather()` — is unaffected) and passed `timeout=60.0` explicitly at the two new call sites.
  - `[medium]` `[patch]` Blind Hunter: no cross-reference anywhere explains why Doctor now carries two structurally-similar "did a `done` key un-finish" checks (`MARSHAL_DURABILITY`'s working-tree-vs-HEAD guard and this story's `LEDGER_REGRESSION`'s revision-range guard) — a future maintainer could mistake one as redundant with the other and merge/delete the wrong one. Fixed: added a paragraph to `sources/ledger.py`'s module docstring explaining the distinction (local/immediate vs. CI/revision-range) and that neither supersedes the other.
  - `[low]` `[patch]` Blind Hunter: two untested branches in `sources/ledger.py`'s `gather()`/`_check()` — a ledger appearing for the first time between `base`/`head` (`before_text is None: continue`), and multi-project aggregation (a regression in one project's ledger must not suppress or merge with a regression in another, and a clean third project must not false-positive). Fixed: added `test_new_ledger_at_head_is_not_a_regression` and `test_regressions_across_multiple_projects_are_all_reported_independently`.
  - `[low]` `[patch]` Blind Hunter: multi-feed aggregation in `gather_story_status` (a false-green in one station's Tier-3 feed must not suppress/merge with another station's, and a clean third station must not false-positive) had no test. Fixed: added `test_false_greens_across_multiple_station_feeds_are_all_reported`.
  - `[low]` `[patch]` Blind Hunter: `sources/ledger.py`'s evidence truncated `keys` to `[:20]` with no explanation for diverging from the source script's own `[:12]` print-truncation bound. Fixed: added a comment noting evidence is structured JSON for an automated consumer, not a scrolled terminal print, so the bound need not match the original's terminal-width choice.
  - `[medium]` `[patch]` Edge Case Hunter: `_harness_tasks` only wrapped the `json.loads(...).get("tasks")` line in try/except; a `state.json` with a non-dict `"tasks"` value (or a non-dict per-task value) crashed with an uncaught `AttributeError` inside the subsequent `.items()`/`.get(...)` loop — a real violation of this module's own "degrades, never crashes" / the spec's "Always: ... never raise" boundary. Fixed: widened the try block to cover the whole per-state-file loop, so a malformed record is skipped whole (any entries from that same file already written before the malformed key are still kept — a strict improvement over losing the entire multi-project scan, which is what an uncaught exception would otherwise do to the whole `gather_story_status` call).
  - `[medium]` `[patch]` Edge Case Hunter: `feed.read_text(encoding="utf-8")` was guarded only by `except OSError`, missing `UnicodeDecodeError` (a `ValueError`) on a non-UTF-8 feed file — same "never raise" boundary violation as above. Fixed: widened to `except (OSError, UnicodeDecodeError)`.
  - `[low]` `[patch]` Edge Case Hunter: `gather_story_status`'s `audited` total was only attached to evidence on the all-clean OK Finding; it was silently absent from every FAIL finding's evidence, so an automated `--json` consumer reading a FAIL finding couldn't tell "3 of 50 audited" from "3 of 3 audited." Fixed: restructured to construct all Findings (FAIL or OK) after the per-feed loop completes, so every Finding's evidence carries the final `audited` total; added an assertion to the existing false-green test and a dedicated multi-feed test confirming the shared final total.
  - `[low]` `[reject]` Blind Hunter: "`_git`/`_parse_statuses` duplicated near-verbatim across `sources/ledger.py` and `sources/marshal.py` instead of a shared helper." Matches this repo's own established tolerance — the two ORIGINAL scripts being ported (`ledger_regression_check.py`/`story_status_check.py`) already duplicate the identical parser between themselves, and no other `sources/*.py` module shares helpers with a sibling either. Introducing a new shared-helper module for a ~15-line dedup is out of proportion to this story's surface (Surgical Changes).
  - `[medium]` `[defer]` Blind Hunter + Edge Case Hunter (independently, both): `gather_story_status`'s Route 3 hardcodes the branch name `"main"` (silent zero-evidence on a repo whose default branch isn't literally `main`, indistinguishable from "checked and found nothing"). Confirmed byte-for-byte inherited from `scripts/story_status_check.py`'s own hardcoded `"main"` — not introduced by this port (spec Design Notes: "preserve, don't redesign"); this repo's own default branch is `main`, so no current-repo impact. Logged to `deferred-work.md`.
  - `[medium]` `[defer]` Edge Case Hunter: `ledger.gather()` never verifies `head`'s resolvability (only `base`'s), so an unresolvable `head` produces spurious `ledger-deleted` FAILs rather than a WARN. Traced to the identical gap in `scripts/ledger_regression_check.py`'s own `main()` (only `base` is `rev-parse --verify`d). Pre-existing, faithfully ported. Logged to `deferred-work.md`.
  - `[medium]` `[defer]` Edge Case Hunter: `_ledger_paths`/`git ls-tree` treats a transient failure identically to "zero ledgers exist," so `gather()` can report a false-clean OK instead of a WARN. Identical to `scripts/ledger_regression_check.py`'s own `ledger_paths(rev)` (`_git(...) or ""`). Pre-existing, faithfully ported. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: rename-continuity tail-matching (`_tail`/`surviving_tails`) can mask a genuine key deletion behind an unrelated new key sharing the same kebab tail. Copied verbatim from `scripts/ledger_regression_check.py`'s own algorithm and its own documented scope (id-migration continuity, not adversarial tail collisions). Pre-existing, faithfully ported. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: a ledger moved to a DIFFERENT project's path between `base`/`head` (cross-path move) is reported as `ledger-deleted` rather than recognized as continuity, since matching is scoped per-path. Identical scope limit in `scripts/ledger_regression_check.py`'s own `check()`. Pre-existing, faithfully ported. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: both new `_git` wrappers only catch `CliBridgeError`; a `UnicodeDecodeError` from `cli_bridge.run_git`'s `text=True` subprocess call could escape uncaught. Confirmed pre-existing in `cli_bridge.py` itself (unmodified, Story 2.1), shared identically by every existing caller including the unmodified `MARSHAL_DURABILITY` `gather()`. A real fix belongs in `cli_bridge.run_git` itself, outside this story's Code Map. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: Route 1's `git log --grep` failure is indistinguishable from "no merge commit found" (both falsy), so a transient git failure could misclassify a landed story as false-green. Inherited from `scripts/story_status_check.py`'s own `sh()` helper's broad exception-to-empty-string swallowing. Pre-existing, faithfully ported. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: Route 3's regex (`^(\d+)-(\d+)-`) only matches canonical numeric keys, unlike `ledger.py`'s own alias-aware `_ID_PREFIX_RE` — a legacy alias-form key never gets Route 3 evaluated. Copied verbatim from `scripts/story_status_check.py`; the inconsistency between the two ORIGINAL scripts pre-dates this story. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: `DONE_RE.findall` doesn't dedupe, so a malformed feed with a duplicate `key: done` line inflates `audited` and can produce duplicate FAIL findings. Identical to `scripts/story_status_check.py`'s own non-deduping loop. Pre-existing, faithfully ported. Logged to `deferred-work.md`.

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 0, medium 5, low 4)
- defer: 11 (high 0, medium 6, low 5)
- reject: 9 (low 9)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both): **the previous pass's headline fix did not work.** `gather_story_status` still raised an uncaught `AttributeError` on a `state.json` mapping a story key to a non-dict value. Reproduced live for `str`, `list` and `int` task values before the fix. Two independent causes: (a) `_harness_tasks`'s widened `try` is structurally unable to catch it — `prev is None or (task.get(...) ...)` short-circuits on a key's FIRST sighting, so `.get` is never evaluated there and the malformed value is stored and detonates in the CALLER's own `task.get("commit_sha")`, which has no guard at all; (b) the same widening introduced a NEW defect — an exception mid-iteration discards every remaining entry in that file, so one malformed record silently un-audits its healthy neighbours (verified: both keys were retained pre-fix, i.e. nothing was "skipped whole" as the comment claimed). Fixed properly: the `try` now guards only the read+parse, and shape is checked per-entry with `isinstance` outside it, so exactly the malformed entry is skipped. Two regression tests added (non-dict values of three shapes; a malformed entry not costing its neighbour), plus one for a non-dict `tasks` payload. The stale comment asserting behavior the code did not have was rewritten to state what it now actually does, and why folding the loop into the `try` is not the equivalent it appears to be.
  - `[medium]` `[patch]` Edge Case Hunter: with git absent or `target` not a repository, BOTH of `gather_story_status`'s git evidence routes fail closed and a story fell straight through to the `phase in NOT_LANDED` test — so it was ACCUSED of being a false green on evidence that was never gathered. Verified live: a non-repo target returned `FAIL warden/1-1-foo: reads 'done' ... with no commit and no merge commit anywhere`. This is a direct violation of the spec's `Always: ... degrade to a WARN/OK Finding on any unreadable/missing input`, and the worst possible failure mode for the detector whose whole job is judging evidence. Fixed by adding the `rev-parse --git-dir` probe the sibling `gather()` in the same module already runs for exactly this reason, returning one WARN. Probed only when feeds exist, so the spec's `No Tier-3 feeds present -> OK, evidence={"audited": 0}` matrix row is preserved byte-for-byte. Test added.
  - `[medium]` `[patch]` Blind Hunter: **neither git evidence route had any success-path coverage.** Every test built a commitless repo, where Route 1 returns `''` and Route 3 returns `None` (both verified directly), so every assertion held via the FAILURE path — deleting either route's implementation left the whole suite green. Route 3 is the most intricate logic in the port (its source script documents two mutation rounds behind its "commit SUBJECT, naming both the slug and `Story <epic>.<seq>`" rule) and landed entirely unpinned. Fixed: four tests added covering both routes' success paths and their near-miss negatives (a merge commit for a NEIGHBOURING key must not launder this one; a subject naming the story number but a DIFFERENT station must not count). Confirmed by mutation: disabling Route 1 now fails `test_merge_commit_naming_the_key_suppresses_the_false_green`, disabling Route 3 now fails `test_hand_landed_commit_subject_on_main_suppresses_the_false_green`; both were green under the old tests.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both): Route 3 recomputed `git log --format=%s main` — a full history walk, plus a subprocess spawn and a lowercase+splitlines over ~2,169 subjects — once per candidate key, though the answer is loop-invariant for the whole gather (`target` never changes). O(keys x history) shell-outs, in the one package carrying an explicit NFR-4 wall-clock budget test. Fixed by computing it lazily once per gather call and reusing it; behavior-preserving.
  - `[medium]` `[patch]` Blind Hunter: the two new test files introduced the doctor suite's first real-`git` dependency without hardening it — no `--initial-branch`, no `commit.gpgsign=false`, no `core.hooksPath` neutralization, and no isolation from an inherited `GIT_DIR`/`GIT_WORK_TREE` (which `cli_bridge.run_git` forwards verbatim via `env=dict(os.environ)`, so the module under test inherits them too). A contributor with commit signing or a global pre-commit hook would get errors rather than failures. The story-status helper also omitted `capture_output`, leaking git's output into pytest's. Fixed in both files: scrubbed git env, explicit `--initial-branch=main` (which for story-status is more than cosmetic — Route 3 queries the literal ref `main`, so a contributor defaulting to `master` would silently exercise a different code path than CI), signing and hooks disabled, and a shared captured `_git` helper.
  - `[low]` `[patch]` Blind Hunter: `ledger.gather` reported the wrong root cause for a non-repository target — `base revision 'origin/main' not resolvable`, sending an operator hunting for a ref problem that does not exist. Fixed by probing `rev-parse --git-dir` on the failure path only (so the healthy path pays nothing) and naming the real cause, mirroring the sibling module's own message. Status stays WARN either way. Test added asserting the message names the repository, not the ref.
  - `[low]` `[patch]` Blind Hunter: `_git`'s new `timeout` parameter hardcoded `30.0` — a copied duplicate of `run_git`'s default — while its own docstring claimed it "defaults to `run_git`'s own default." If `run_git`'s default ever moved, this wrapper would silently pin the old value and the docstring would become false. Fixed: `timeout: float | None = None`, forwarded only when set, so the claim is now structurally true rather than coincidentally true.
  - `[low]` `[patch]` Blind Hunter: `sources/__init__.py` re-hardcoded the source count in prose ("today's 11", "bringing the count to 11") — the previous pass "fixed" the stale `9` by writing a new number that Story 6.5 will stale again. Fixed by removing the number entirely and stating why: `REGISTRY` is the count, `test_sources_registry.py` pins it to `Source` in both directions, so a number in the docstring could only ever be a second source of truth.
  - `[low]` `[patch]` Blind Hunter: the same-commit fallback silently rewrote `base` to a resolved parent SHA, which then surfaced as `evidence["base"]` and inside the `remedy` string with no flag — a `--json` consumer that asked for `origin/main` got a 40-char SHA back and could not tell "you asked for this" from "we substituted." The source script printed an explicit note; a library has no stdout to print on. Fixed by carrying `base_requested`/`base_substituted` in evidence when and only when a substitution occurred. Two tests added (present on substitution, absent otherwise).

### 2026-08-09 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 3, low 5)
- defer: 2 (high 0, medium 2, low 0)
- reject: 10 (low 10)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: **the previous pass's git-environment hardening did not protect the code under test** — the third consecutive pass on this story to find that a headline fix only claimed its coverage. Both new test files built `_GIT_ENV` (os.environ minus `GIT_DIR`/`GIT_WORK_TREE`/…) and passed it to their OWN fixture `subprocess.run` only, while the module under test reaches git through `cli_bridge.run_git`, which does `env = dict(os.environ)` at call time and was never touched. Both files' comments asserted exactly the coverage they lacked ("cli_bridge.run_git forwards os.environ verbatim, so the module under test would inherit them too … Scrub all three at the fixture boundary"). Reproduced: with a decoy `GIT_DIR` exported, the two files ran **13 failed / 15 passed** (clean: 28 passed), and among the casualties was `test_non_repository_target_warns_instead_of_accusing`, which returned FAIL instead of WARN — precisely the regression pass 2 added that test to prevent. Fixed with an autouse `monkeypatch.delenv` fixture in both files (mutating the real environment, which is the only thing `run_git` reads), widened to also cover `GIT_CEILING_DIRECTORIES`/`GIT_COMMON_DIR`; the now-redundant private env dict was removed. Verified after: **35 passed** under the same hostile `GIT_DIR`, and 491 passed for the whole suite under it.
  - `[medium]` `[patch]` Edge Case Hunter: a tracked ledger blob containing a non-UTF-8 byte raised `UnicodeDecodeError` **straight out of `ledger.gather()`** — a direct violation of the spec's `Always: … degrade to a WARN/OK Finding on any unreadable/missing input, never raise`. Reproduced live (a `\xe9` byte in a committed ledger). `cli_bridge.run_git` decodes with `text=True` but catches only `TimeoutExpired`/`OSError`, and both new `_git` wrappers caught only `CliBridgeError`. Pass 1 deferred this as theoretical and belonging in `cli_bridge`; with a live repro and an explicit contract violation in this story's own new code, the local guard lands here (`except (CliBridgeError, UnicodeDecodeError)` in both wrappers, in-Code-Map) while the shared `cli_bridge`-level fix for every caller stays deferred. Regression test added asserting `gather` returns rather than raises.
  - `[medium]` `[patch]` Blind Hunter: **the OK Finding asserted landing evidence for stories it deliberately never checked.** `gather_story_status` counts every `done` key into `audited` — including the ones on the silent `task is None` branch — then reported "every `done` story is backed by a merge commit or a recorded commit sha (N audited)". Measured against this repo: **audited=27, of which 19 had no run record at all** and only 3 ever reached a git evidence route, so ~70% of the population the message vouched for was unmeasured. The source script mitigated this with `--verbose` (`(no run record -- hand-landed or pre-loop)`); the port inherited the claim and dropped the qualifier. Fixed: the message now states the weaker claim the gather actually establishes — "no `done` story contradicts its landing evidence" — with the previously `--verbose`-only breakdown folded in. Folded in the same fix (Blind Hunter, separately): a malformed run record was silently indistinguishable from "no run record", turning corrupt harness state — exactly what a broken loop run leaves behind — into a clean pass; `_harness_tasks` gained an optional `skipped` accumulator (default `None`, so the existing two-arg call and its tests are unaffected) and unreadable records are now counted in the message. The breakdown went into the message rather than `evidence` **on purpose**: the spec's I/O matrix pins this Finding's evidence to exactly `{"audited": 0}` for the no-feeds row, so widening the shape would be a spec deviation — enriching it stays deferred. Three tests added.
  - `[low]` `[patch]` Blind Hunter: `ledger.gather`'s two cannot-evaluate WARNs disagreed on their own evidence shape — unresolvable-base emitted `{"base","head","target"}`, base==head-with-no-parent emitted `{"base","head"}`. Same source, same check, same status, so a consumer reading `evidence["target"]` got a `KeyError` on one of two paths (pass 2 added `target` to one branch and did not carry it six lines down). Fixed; test asserts both WARNs now carry identical evidence keys.
  - `[low]` `[patch]` Blind Hunter: `evidence["keys"]` carried two different shapes under one field name — pre-formatted `"<key> (<old> -> <new>)"` display strings for `done-key-regressed`, bare keys for `ledger-deleted` — while the comment directly above it justified the field's truncation bound *because* it is "structured JSON for an automated `--json` consumer, not scrolled." The data contradicted its own defence. Fixed: `keys` is bare story keys under both kinds, and the transition travels beside it already parsed as `transitions: [{"key","from","to"}]`. Test added.
  - `[low]` `[patch]` Blind Hunter: `ledger.gather`'s OK Finding recorded nothing about what it compared, so "8 ledgers compared, all clean" and "0 ledgers found, vacuous green" were the same report — making the already-deferred OK-over-an-empty-measurement defect undiagnosable from the output. `_check` now returns the compared-path count alongside its findings and `ledgers_compared` rides in evidence. This does NOT change the OK-vs-WARN verdict (that decision stays deferred); it makes the deferred decision visible meanwhile. Test covers both the populated and the zero case.
  - `[low]` `[patch]` Blind Hunter: `sources/ledger.py`'s cross-reference paragraph — added in pass 1 specifically so a maintainer would not mistake `MARSHAL_DURABILITY`'s guard as redundant with this one — stopped short of the one place the two guards genuinely contradict each other: they answer "I cannot see any ledger at all" in opposite directions (sibling WARNs `ledger-inventory`; this module returns OK). Named in the paragraph, pointing at the deferred entry that owns the resolution.
  - `[low]` `[patch]` Blind Hunter: `test_source_has_exactly_eleven_members` baked into a test *name* the very count pass 2 had just deleted from `sources/__init__.py`'s prose for being a second source of truth ("it already did once, at 9"). Story 6.5 would make the name a lie while the set-equality assertion inside still passed. Renamed to `test_source_taxonomy_is_exactly_this_closed_set`, with the rationale in the comment.
  - `[medium]` `[defer]` Blind Hunter: Route 1's `git log --oneline --all -F --grep` still spawns one all-refs history walk PER candidate key — the more expensive of the two routes is the one pass 2 did not hoist (measured: 20 of 22 git calls in a 20-key fixture were Route 1). Not patched because, unlike Route 3's genuinely loop-invariant query, Route 1's grep is key-specific AND matches the full commit message, so a hoist requires re-implementing the match in Python over `--format=%B` — a semantics-carrying restructure, not a review patch. Logged to `deferred-work.md`.
  - `[medium]` `[defer]` Edge Case Hunter: `ledger.gather()` silently requires `target` to be the repository ROOT — `ls-tree`/`git show` run with `cwd=target`, so a subdirectory target lists only that subtree, matches no `_bmad-output/projects/` path, and reports a real regression as a clean OK. Reproduced live. NEW exposure (the original script hardcoded `REPO_ROOT`; the `cwd=target` port introduced it), but every candidate fix changes what `target` MEANS for this source and the same repo-root assumption is shared by the sibling `gather`, so it belongs to whichever story owns target resolution. Logged to `deferred-work.md`.
  - `[low]` `[reject]` x7 Edge Case Hunter: unresolvable `head`; tail-collision masking a genuine loss; Route 3's hardcoded `main`; Route 3's non-alias-aware regex; `_parse_statuses` inline-comment/quoting; `DONE_RE`'s narrow accepted shape; `DONE_RE` non-dedupe. All seven are already recorded in `deferred-work.md` from passes 1 and 2 — verified individually against the ledger's existing 20 entries for this spec. Re-deferring would duplicate them.
  - `[low]` `[reject]` Blind Hunter: `check="story-status"` used for OK/WARN/FAIL alike, versus the sibling's per-condition check names. The check-name taxonomy question is already deferred from pass 2 with a reasoned decision ("several existing tests assert the current string and check-name taxonomy is not this story's surface"); re-opening it here would re-litigate a decided call.
  - `[low]` `[reject]` x2 Blind Hunter: `_git`'s `**kwargs` forwarding should be a two-branch `if/else` (style; the current form was itself a pass-2 fix and is correct), and the three-shape malformed-value test should use `@pytest.mark.parametrize` (test-readability nit, no coverage difference).

### 2026-08-09 — Review pass (follow-up 3)
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 1, medium 7, low 3)
- defer: 2 (high 0, medium 2, low 0)
- reject: 12 (low 12)
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: **`gather_story_status` raised `TypeError` out of the gather on a `state.json` giving a story's `phase` a list or dict value** — `phase in NOT_LANDED` hashes `phase`, and `_harness_tasks`'s `isinstance(task, dict)` guard (added in pass 2 for exactly this class) validates the CONTAINER while `phase` is the only value fed to a hash-requiring operation. Reproduced live for `list` and `dict`. This is the fourth consecutive pass to find a malformed-`state.json` crash in the same function and the third to find one the previous pass's guard did not actually cover; the guard is now on the value, where the hazard is. Fixed (`isinstance(phase, str) and phase in NOT_LANDED`), test covers three shapes.
  - `[medium]` `[patch]` Edge Case Hunter: `gather_story_status(target)` with the default `loop_root` raised `RuntimeError` from `Path.home()` when `HOME` is unset and the uid has no passwd entry (the ordinary rootless-container shape) — escaping before any Finding could be built, including for the no-feeds row the spec documents as a vacuous OK. Reproduced live. Fixed: degrades to "no harness records visible" (`_harness_tasks` now accepts `loop_root=None`), so every audited story reads as "no run record" rather than the call dying. Test added.
  - `[medium]` `[patch]` Blind Hunter: **pass 3's `_git` hardening silently changed the shipped `MARSHAL_DURABILITY` `gather()`** — the widened `except (CliBridgeError, UnicodeDecodeError)` is on the wrapper both gathers share, so an undecodable committed ledger blob stopped raising and started returning `None`, which `gather()` reads as "not committed." Reproduced live: a tracked ledger with a `\xe9` byte and three wiped `done` markers reported `WARN ledger-untracked: sprint ledger exists on disk but is not committed` — factually false, the regression comparison skipped in silence, and the operator sent to fix a problem that does not exist. Fixed by asking git which case it is (`ls-tree --name-only HEAD -- <path>`, probed only on the already-failing path) and emitting a `ledger-unreadable` WARN when the blob IS tracked. Reverting the catch instead would restore a crash the module's own docstring forbids; this keeps the verdict honest in both directions.
  - `[medium]` `[patch]` Blind Hunter: the same conflation in `sources/ledger.py`, in the more dangerous direction — an unreadable blob at `base` is indistinguishable from "this ledger did not exist at base," which `_check` skips as "nothing to regress," so **a ledger that un-finished two stories between the two revisions reported a clean OK** — with `ledgers_compared: 1` positively asserting the ledger had been compared. Reproduced live against a control that correctly FAILs. Fixed: `_check` now consults the two `ls-tree` listings (already in hand) to tell absence from unreadability, and emits a cannot-evaluate WARN for the latter.
  - `[medium]` `[patch]` Blind Hunter: the mirror case at `head` — an undecodable blob produced a `ledger-deleted` **FAIL carrying a `git checkout <base> -- <path>` remedy** for a ledger that is still there, so following the printed remedy discards the head ledger over what may be a purely cosmetic edit. The pass-3 patch satisfied "never raise" and left the finding in the FAIL branch, trading one contract violation for another; its test asserted only that `findings` was truthy, explicitly accepting the FAIL. Fixed by the same listing check (WARN, no remedy); the test now asserts the status and the absence of a remedy.
  - `[medium]` `[patch]` Edge Case Hunter: **a valid repo with no local `main` convicted hand-landed stories.** Route 3's `git log --format=%s main` fails there (a PR checkout, a shallow clone, a differently-named default branch), and `or ""` collapsed the failure into "queried, found nothing," so the story fell through to the harness verdict and was accused of being a false green. Pass 2's repo-level `rev-parse --git-dir` probe does not cover it — the repo is perfectly valid. Reproduced live with a control: identical repo, branch `main` → OK; renamed to `pr-branch` → FAIL. Fixed by keeping the query's `None` (failure) distinct from `""` (no match) on BOTH routes and counting such keys as inconclusive rather than convicting them. The hardcoded branch NAME remains deferred (pass 1); this fixes the conviction, which is the harmful half.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both): **pass 3's malformed-record counter missed the corruption it was written for.** A truncated `state.json` — the likeliest state a killed loop run leaves — fails at `json.loads`, which takes the *file-level* `except Exception: continue` that never touched the counter; only the synthetic per-entry case was counted, and only that case was tested. Measured: a truncated record reported "2 audited, 2 with no run record (unchecked)", indistinguishable from two genuinely hand-landed stories. Fixed: `_harness_tasks` now also accumulates unreadable run-record FILES (they have no keys to attribute), reported as their own caveat clause. Test added.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both): the counter that did fire produced numbers that do not reconcile — malformed entries were accumulated per (run-file x key) with no intersection against the audited key set and no cross-station scoping, so one audited story with three unrelated malformed records printed **"1 audited, 3 run record(s) unreadable"** (a caveat exceeding its own denominator, qualifying a result whose evidence was in fact complete), and a record superseded by a later valid run was still counted. Fixed: the accumulator is a per-station key set, intersected with the keys actually audited. Two tests added.
  - `[medium]` `[patch]` Edge Case Hunter: a sprint feed that cannot be read drops a WHOLE station from the audit, and the OK Finding said nothing about it — a confident green over a station never opened, in the detector whose sole purpose is catching confident greens. Fixed with a caveat clause naming the count. Deliberately message-only: the deferred entry that owns this notes a WARN + `evidence` counter would change the OK Finding's evidence shape, which the spec's I/O matrix pins — so the part that needs the contract stays deferred and the part that does not is fixed now.
  - `[medium]` `[patch]` Edge Case Hunter: a third unchecked population went unnamed — a story with a run record, no `commit_sha`, no merge commit, no main-subject match, and a `phase` outside `NOT_LANDED` (e.g. `review-running`) reaches the end of every route with nothing found, yet was counted into `audited` as though verified. Measured live: exactly one today, and it is this very story. Fixed with its own caveat clause; the live run now reads "27 audited, 19 with no run record (unchecked), 1 with no landing evidence and no harness verdict."
  - `[low]` `[patch]` Blind Hunter: both documented defaults had **zero automated coverage** — every test passed `base=`/`head=`/`loop_root=` explicitly, so `".bmad-loop"` for `".bmad-loops"` or `"main"` for `"origin/main"` would have shipped green, in a story whose own Design Notes make the defaults a contract. Two tests added exercising `ledger.gather(repo)` and `gather_story_status(target)` with no arguments. Folded in the same fix: `ledgers_compared` counted LISTED paths rather than ledgers actually read (so the field added in pass 3 to make an empty measurement visible reported an unread ledger as compared) — it now counts only ledgers whose blobs were both fetched and parsed.
  - `[medium]` `[defer]` Blind Hunter: `MARSHAL_DURABILITY` `gather()`'s working-tree `ledger.read_text` catches `OSError` only, so a non-UTF-8 byte on disk still raises — the last hazard in the module treated differently from its neighbours, and a live contradiction of the module docstring's "never crashes." Reproduced. Not patched: the line pre-dates this story and the spec's **Never** forbids changing `gather()`'s behavior (the untracked/unreadable fix above corrects a change THIS diff made; this would be a new one). Logged to `deferred-work.md`, and the gap is now named in the docstring so the claim is not read as unqualified.
  - `[medium]` `[defer]` Blind Hunter + Edge Case Hunter (independently, both): `audited`/`no_record` count `epic-N` aggregate rows as stories — measured live, 5–6 of 27, all landing in the no-record bucket, inflating both numbers the pass-3 breakdown reports. `DONE_RE` is verbatim from the source script (which counted nothing, so the inflation only became visible once the breakdown existed). Filtering means deciding the key grammar — the same decision two existing deferred entries turn on — so all three want resolving together. Logged to `deferred-work.md`.
  - `[low]` `[reject]` x7: unresolvable `head`; `ls-tree` C-quoting of non-ASCII paths; the hardcoded branch name `main`; Route 3's non-alias-aware regex; `_parse_statuses` inline-comment/quoting; the two guards disagreeing on "no ledger at all"; `check="ledger-regression"` emitted by two sources. All seven verified individually against the ledger's existing 24 entries for this spec — already recorded in passes 1–3.
  - `[low]` `[reject]` Blind Hunter: the two new test files hard-depend on a `git` binary not declared in `[feature.pyforge-doctor.dependencies]` (32 fail if git is off `PATH`). Declining: git is a hard prerequisite of the whole repository and of `cli_bridge` itself — the module under test shells out to it — so a suite that SILENTLY SKIPPED its only real-git coverage when git is absent would be a false green, precisely the defect class this story exists to prevent. Failing loudly is the correct behavior; declaring the dep is a pixi-surface change outside this story's Code Map.
  - `[low]` `[reject]` Blind Hunter: story-status's three Findings share one `check` name with three evidence shapes. The OK Finding's evidence is pinned to `{"audited": N}` by the spec's I/O matrix, so unifying the shapes is a spec deviation, already recorded as deferred; the check-name half was decided in pass 2.
  - `[low]` `[reject]` x3: a project directory named literally `pyforge-` yields an empty slug that matches every commit subject (no such directory exists or can, given the `pyforge-<slug>` convention); the FAIL path not carrying the new caveat counts (a FAIL is an accusation about one named story, not a completeness claim — now stated in a comment rather than duplicated as evidence); `_git`/`_parse_statuses` duplicated across the two modules (rejected in pass 1 for the same reason).

## Design Notes

`gather()`'s `base`/`head` (ledger.py) and `loop_root` (marshal.py) are
keyword-only optional parameters, deliberately diverging from the sibling
sources' plain `gather(target)` signature — this is the FIRST Doctor source
whose correctness depends on a revision range or a host-state root path
rather than `target` alone, and there is no production caller yet (mirrors
Story 6.2/6.3's own accepted "zero production callers" precedent) to force a
narrower signature. Defaults (`"origin/main"`/`"HEAD"`/`Path.home() /
".bmad-loops"`) exactly match each original script's own hardcoded behavior.

`story_status`'s `scope="repo"` classification is preserved as-is even though
`_harness_tasks` reads `~/.bmad-loops` (host state): the script's own current
`DETECTOR` declaration already says `"repo"`, and it degrades to a vacuous
`audited=0` OK Finding in CI (Tier-3 feeds are gitignored, so the glob finds
nothing) rather than crashing or reading stale host state incorrectly — the
same reasoning that lets it run safely today. Redesigning the scope split is
explicitly out of this story's surface (Epic 6 context, Known Blocker 4:
"survive the move," not "correct" it).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done` (fourth review pass on an already-implemented story; no
implementation loopback — 0 `intent_gap`, 0 `bad_spec`).

**Summary.** A review-only pass over `f9fc4cbf28..HEAD`. Eleven patches landed,
all of them corrections to the story's own new code or to a prior review pass's
fix. The through-line: this port's two gathers must "degrade to a WARN/OK
Finding on any unreadable/missing input, never raise" (spec **Always**), and
three separate branches were still violating it in one direction or the other —
raising outright, or degrading so far that a cannot-evaluate became a verdict.
Two crashes were fixed, three false verdicts (a false green over a real
regression, a destructive-remedy FAIL over a cosmetic edit, a FAIL conviction on
evidence that was never gathered) were converted to honest WARN/inconclusive
outcomes, and the OK Finding's breakdown now reconciles against its own
denominator.

**Files changed (4):**
- `src/.../doctor/sources/ledger.py` — `_check` distinguishes "absent at this
  revision" from "listed but unreadable" using the two `ls-tree` listings it
  already computes; unreadable becomes a `ledger-unreadable` WARN with no
  remedy; `ledgers_compared` counts ledgers actually read, not merely listed.
- `src/.../doctor/sources/marshal.py` — `gather()` distinguishes untracked from
  unreadable before accusing a committed ledger of being uncommitted;
  `gather_story_status` guards a non-string `phase`, survives an unresolvable
  `Path.home()`, keeps a failed git query distinct from a query that found
  nothing on both evidence routes, and reports five separate unverified
  populations in its green's caveat instead of one.
- `tests/unit/test_sources_ledger.py` — the non-UTF-8 test now pins WARN and the
  absence of a remedy (it previously accepted the FAIL); new tests for the
  unreadable-at-base false green and for the documented `base`/`head` defaults.
- `tests/unit/test_sources_marshal_story_status.py` — `_init_repo` gains a
  baseline commit so `main` exists and both routes actually run (the fixtures
  previously reached every assertion via a route that could not execute); nine
  new tests, one per patched defect.

**Review findings:** 11 patched (1 high, 7 medium, 3 low), 2 deferred (both
medium, appended to `deferred-work.md` as new entries), 12 rejected (all low —
seven verified duplicates of existing ledger entries, five reasoned declines).

**Verification:**
- `pytest tests -q` against the worktree's own sources (`PYTHONPATH` pinned per
  the note below): **502 passed** (was 491). Re-run under a hostile
  `GIT_DIR=/tmp/decoy-gitdir`: **502 passed**.
- `ruff check src tests`: 35 findings, byte-identical to the baseline revision's
  count and none in any of the four changed files (verified by `git stash`
  comparison).
- Live gather against this repo: `ok ledger-regression | no tracked ledger
  un-finishes a story between origin/main and HEAD`; `ok story-status | no
  `done` story contradicts its landing evidence (27 audited, 19 with no run
  record (unchecked), 1 with no landing evidence and no harness verdict)`.
- Every patched defect was reproduced live BEFORE the fix and re-run after
  (repro scripts kept out of the repo); each has a regression test, and the four
  false-verdict fixes were checked against an all-ASCII / branch-present control
  that still produces the correct FAIL.

**Residual risks:**
- Two new deferred entries (the working-tree `read_text` decode gap inside the
  off-limits `MARSHAL_DURABILITY` `gather()`, and `epic-N` rows inflating the
  audit's denominator) are recorded, not fixed.
- `_init_repo` gaining a baseline commit changes how four pre-existing
  false-green tests reach their assertions. This is a strengthening — they
  previously passed through a route that could not execute — but it is a fixture
  semantics change, and it is the reason those four tests kept passing across
  the Route-3 conviction fix.
- Neither gather has a production caller yet (spec-mandated: no `__main__.py`
  wiring until a later story), so only `MARSHAL_DURABILITY` — the one source
  already wired — has live blast radius today.
