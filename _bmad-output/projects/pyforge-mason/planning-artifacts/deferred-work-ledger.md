---
doc_type: deferred-work-ledger
project: pyforge-mason
date: 2026-07-31
status: promoted-verbatim
---

# pyforge-mason — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-31 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown. Until today this project had **no tracked
ledger at all**, so its entire deferred-work record — 4 KB, 4 entries — existed
only in scratch space. Produced by the 2026-07-30/31 six-station fleet run and found
by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current.

**The one intentional edit is id assignment.** bmad-loop's damping output writes either
no id or a generic `DW-<n>`, which collides the moment another story is damped. Each
entry here is keyed `DW-<story>-<n>` from its own `source_spec`, per the convention the
sibling ledgers and the detector both use.

---

### DW-1-3-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-error-taxonomy-and-exit-code-contract.md`
  summary: `cli.py`'s stderr writes (the new `except MasonError` handler's `print(str(exc), file=sys.stderr)`, the pre-existing `except Exception` handler's `traceback.print_exc()`, and `parser.print_help(file=sys.stderr)`) are all unguarded against `OSError`/`BrokenPipeError` if stderr is closed or piped-and-closed, which would let the write itself escape `main()`'s except block uncaught instead of landing on a documented exit code.
  evidence: Confirmed by direct inspection — none of `main()`'s three stderr-write call sites (old or new) wrap the write itself in a try/except; this is a pre-existing pattern across the whole file (the `except Exception` handler's `traceback.print_exc()` and the bare-noun branch's `parser.print_help(file=sys.stderr)` both predate this story unchanged), not something newly introduced by Story 1.3's `MasonError` handler alone. A proper fix belongs to a single pass across all of `cli.py`'s stderr call sites together (most naturally once Story 1.4's `render.py` becomes the sole output writer), not a one-off guard added around just the new call site in isolation.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-1-3-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-error-taxonomy-and-exit-code-contract.md`
  summary: `tests/meta/test_exit_code_ownership.py`'s `_find_rogue_exit_code_owners` calls `path.resolve()` (to compare against the owner path) before entering the `try`/`except OSError` block that protects `read_text`, so a path that raises `OSError` on `resolve()` itself (e.g. a symlink loop, `ELOOP`) would escape as a raw traceback instead of the file's own documented clean-`AssertionError` contract.
  evidence: Confirmed by direct inspection of the new file's `_find_rogue_exit_code_owners`, and this is not a new defect introduced by Story 1.3 — the file's own docstring states it "mirrors `test_dependency_direction.py`'s approach," and that pre-existing file's `_find_subprocess_importers` has the identical `path.resolve() in allowed` check ahead of its own `try` block (confirmed by reading that file). Fixing only the new file would be inconsistent with the sibling it deliberately mirrors; a proper fix belongs to both meta-test files together in one pass, not a unilateral deviation introduced here.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-1-4-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`
  summary: `render.py`'s `write()` calls `stream.write(...)`/`stream.flush()` with no `BrokenPipeError`/`OSError` guard, so `mason doctor | head -1` (or any consumer that closes the pipe early) would let the write itself escape uncaught into `main()`'s generic `except Exception` handler — a raw traceback and `EXIT_INTERNAL` instead of a clean, expected broken-pipe exit.
  evidence: Confirmed by direct inspection — `write()`'s two-line body has no try/except around the stream I/O. This joins the exact same family already logged above from Story 1.3 (`cli.py`'s stderr writes are unguarded the same way) rather than duplicating it: that entry already recommends "a single pass across all of `cli.py`'s stderr call sites together, most naturally once Story 1.4's `render.py` becomes the sole output writer" — but Story 1.3's `MasonError`-handler call site doesn't exist in this branch yet (developing in an unmerged sibling worktree), so a unified pass covering every stdout+stderr write call site together isn't possible until that merges. Fixing only `render.py`'s new call site now would repeat the same piecemeal-fix problem the existing entry warns against.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-1-4-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`
  summary: `render_json`/`render_text` have no defensive handling for a `data`/`errors` value `json.dumps` can't serialize (e.g. a `Path` or `datetime`) — `render_json` would raise an unhandled `TypeError` instead of a clean, actionable failure.
  evidence: Confirmed by direct inspection — no `default=` fallback or type-normalization exists before the `json.dumps` call. Not triggered by any current caller (`doctor`'s stub only ever passes a plain string `message`), so it is not a defect in this story's own delivered scope; it will matter once `recipe.py`/`package.py`/`environment.py` land in later epics and start returning richer data shapes (paths, versions, timestamps) through `render.write`.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-1-10-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: follow-up review still recommended for 1-10 after the damping cap was spent — an independent pass is owed on the configuration surface, logging, and child-output streaming.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260809-231234-a3cb`. 1-10 also ran to both ceilings — dev attempt 2/2 and review cycle 3/3 — and cleared on its LAST cycle rather than escalating, which is exactly the profile where an independent pass is worth spending.
  promoted: 2026-08-10 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there) under THIS ledger's own `DW-<story>-<n>` convention (`DW-1-3-1`, `DW-1-4-1`, `DW-1-4-2`), which differs from doctor's and atlas's `DW-FU-<story>`; the station's own precedent wins. A generic `DW-1` would collide with the next damped story, and Tier-3 is gitignored so the entry would not survive a clone. Marshal Story 4.13 — landed earlier today in PR #381 — exists to make this promotion an obligation of the story rather than archaeology someone performs later.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2: Follow-up review still recommended for 2-2-the-seam-guard after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-2-2-the-seam-guard.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-193147-b96d; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, mason 2-2 / marshal 7-4)

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-3-1

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-3-credential-isolation.md`
  summary: follow-up review still recommended for 2-3 after the damping cap was spent — an independent pass is owed on the AD-14 credential-isolation guard.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260810-193147-b96d`. The story ran to 3 review cycles, each closing real bypasses (env aliasing, indirect mutation methods, non-assignment binding targets, explicit-environment spawn functions), which is the profile where an independent pass is worth spending.
  promoted: 2026-08-11 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-3` there) under this ledger's own `DW-<epic>-<story>-<n>` convention, renamed to avoid colliding with the next damped story (bmad-loop always emits a generic id).
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-5

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `test_every_sanctioned_yaml_exception_is_live_and_import_form_scoped` (`tests/meta/test_no_config_file.py:194-228`) does not enforce the invariant its own docstring claims. It asserts only on `ast.ImportFrom`, but the sanctioned `import yaml` form exposes `yaml.unsafe_load` identically via attribute access, and `_SANCTIONED_YAML_EXCEPTIONS` keys on `(path, banned_module)`, blanket-exempting the whole file.
  evidence: Review-verified live — substituting `yaml.unsafe_load` for `yaml.safe_load` in `_read_content_hash` leaves the meta suite green. Fix: add an `ast.Attribute` walk asserting `yaml.<attr>` is only ever `safe_load`.
  severity: medium
  status: open
  promoted: 2026-08-15 — the story 4.4 review pass that found this escalated CRITICAL on an unrelated intent gap before any of its findings could be applied ("no patches were applied and no ledger entries were written -- the intent gap makes every lower finding moot"); recovered from the run's own raw session log (`.bmad-loop/runs/20260814-202334-1831/logs/4-4-mason-environment-check-review-2.log`) during `/bmad-loop-resolve` so it is not lost when the run directory is eventually cleaned up.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-6

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: FR-28 — the sole FR Story 4.4 realizes (`epics.md:114`, `:1210`) — is cited nowhere in the package (`grep -rn "FR-28" src tests` returns 0 hits, vs. 17 for FR-25 and 20 for FR-27). Every new Story 4.4 docstring/comment (`errors.py:812,870,928`; `condalock.py:70,242`; `cli.py:1371`) cites FR-25/FR-27/FR-29 — the sibling story's FRs, copied wholesale.
  evidence: Review-verified via direct grep against the delivered code.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-7

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `CondaLockCheckResult`'s `stdout` field docstring (`condalock.py:242-253`) claims it "mirror[s] `CondaLockResult`'s own identical fields **and rationale**" — but that rationale ("a failure investigated outside a live terminal needs diagnostic text, not a bare returncode integer") is false for `check()`: the field is structurally always empty, since `stderr=None` inherits and this module's own docstring states conda-lock writes every progress/diagnostic line to stderr and nothing to stdout on either outcome.
  evidence: Review-verified by direct inspection of `condalock.py`.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-8

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `EnvironmentCheckTimeoutError`'s docstring (`errors.py:944-946`) says `timeout` is "the number of seconds that **elapsed** before the child was killed"; the call site (`condalock.py:389`) actually passes `resolved_timeout`, the configured *limit*. Copied verbatim from `EnvironmentLockTimeoutError` (`errors.py:781-782`), which carries the identical pre-existing inaccuracy — the new class propagated it rather than correcting it.
  evidence: Review-verified by direct inspection; the sibling class's own copy is pre-existing (not introduced by this story).
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-9

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: the after-invocation lockfile read misattributes engine-side corruption to the user. Both reads call `_read_content_hash(temp_lockfile_path, lockfile_path)` (`condalock.py:367,387`), and the helper names the *second* argument in its error message. The before-read already proved the caller's file parses, so an after-read failure (conda-lock killed, or `$TMPDIR` filling mid-rewrite and truncating the temp copy) can never be the caller's file's fault — yet it raises `EnvironmentLockfileMalformedError` naming the user's own intact lockfile and prescribing regeneration.
  evidence: Review-verified by direct inspection of the two call sites and the helper's error-naming behavior.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-10

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `check()`'s argv test asserts via `argv.index("-f")`/`argv.index("-p")` against single-element inputs only (`_MANIFEST_PATHS = ("environment.yml",)`, `platforms = ("linux-64",)`), so it would pass even if `check()` emitted only the first manifest or platform of a multi-element list. `check()` re-implements `lock()`'s repetition loops rather than sharing them, and `lock()` has its own multi-element regression tests (`test_lock_with_multiple_platforms_repeats_dash_p_in_order`, `test_lock_with_multiple_manifests_repeats_dash_f_in_order` — `test_engines_condalock.py:219,234`) that `check()` has no equivalent of.
  evidence: Review-verified by direct inspection of the test suite.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-11

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `environment lock`'s dispatch returns `EXIT_OK` unconditionally (`cli.py:1381-1388`), so a failed solve that wrote no lockfile still exits 0 — the exact opposite policy to the `returncode`-projection this story's own first review pass added to `check`'s dispatch, whose own comment argues "a CI gate must not green-light on its own internal failure." Pre-existing (Story 4.3); the two sibling verbs on one noun now disagree with each other.
  evidence: Review-verified by direct inspection of both dispatch branches in `cli.py`.
  severity: medium
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-12

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: every conda-lock diagnostic names the temp copy's path, not the user's real lockfile (e.g. `.../tmp/mason-condalock-check-vedwraei.yml is missing a version`). The path is one the user never supplied, the `finally` block unlinks it before they can inspect it, and nothing maps the message back to their own file. Contrasts with `_read_content_hash`'s own errors, which are careful to name `lockfile_path` (the user's real path) — the child process's own output is never re-mapped at all. A consequence of this story's temp-copy design (necessary so the user's file is never mutated).
  evidence: Review-verified by direct inspection of the temp-copy flow and cleanup.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-13

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `--format json` emits no JSON at all on any typed-error path. `main()`'s `except MasonError` handler (`cli.py:1456-1460`) prints `str(exc)` to stderr and returns `EXIT_FAILED` with stdout left empty — but the frozen spec's own intent-contract states a JSON envelope on both the success path (`:1202-1204`) and a typed-error path (`:1206-1208`) of the same contract.
  evidence: Review-verified by direct inspection of `main()`'s exception handling against the frozen spec's own stated contract.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-10-1: `recipe update`'s default (non-`--dry-run`) apply has no VCS safety net and shows a thinner plan than `--dry-run`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-10-mason-recipe-update.md`
  summary: Two related residual risks in the deliberate default-writes-for-real design (spec Design Notes, four independent citations including the architecture spine's own "defaults to it where the operation is irreversible" convention): (a) a `recipe_path` outside a git working tree has no VCS safety net against a first, unconfirmed write -- `context.version`/`build.number`/`source.*.sha256` are overwritten with no confirming flag, unlike `submit`'s `--yes`; (b) the default apply path's own stdout narration ("New version found: X") shows only the target version, never the full field-level `actions` plan `--dry-run`'s JSON body carries, a materially thinner "displayed before written" guarantee than the dry-run path gives.
  evidence: Confirmed by reading `recipe_updater.py`/`github_updater.py` directly -- the real-write JSON body (`{"success": true, "updated": true, "new_version": ..., "message": ...}`) genuinely omits the `actions` list the dry-run body carries. Raised by adversarial review (Blind Hunter) against the Story 2.10 diff, 2026-08-12; the out-of-git scenario is not reachable via Mason today (Story 2.4, `mason recipe new --output`, is still `backlog` -- no Mason verb can place a recipe outside `recipes/` yet) but is reachable via any hand-placed `recipe.yaml`, so the risk is real even if the specific repro cited isn't yet Mason-native. Reviewed against the spec's own citations and judged not to overturn a deliberate, evidenced decision inside the same pass that made it -- logged for a future dedicated look (e.g. an explicit confirming flag mirroring `submit`'s `--yes`, or a git-tracked-path check) rather than reversed here. Not this story's defect so much as its stated tradeoff's open follow-up.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-10-2: CFE's `recipe_updater.py` hardcodes the bare command `"python"` for its internal `recipe_editor.py` subprocess call, unlike its sibling `github_updater.py`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-10-mason-recipe-update.md`
  summary: `recipe_updater.py`'s real-write path spawns `["python", str(RECIPE_EDITOR_SCRIPT), ...]` -- a bare PATH lookup -- while its sibling `github_updater.py` correctly resolves `os.environ.get("CONDA_PYTHON_EXE") or sys.executable` for the identical internal call. If the CFE-resolved interpreter's environment has no `python` alias on `PATH` (only `python3`, for instance), the PyPI default-apply path fails at this inner subprocess call -- a portability gap in the wrapped tool itself, not in Mason's adapter.
  evidence: Confirmed by reading both scripts directly (`.claude/skills/conda-forge-expert/scripts/recipe_updater.py` line ~141 vs. `github_updater.py` line ~244). Raised by adversarial review (Blind Hunter) against the Story 2.10 diff, 2026-08-12. AD-15 forbids a Mason-side fix (no implementation commit may write `.claude/skills/conda-forge-expert/**`); Mason's own fixture stubs short-circuit before this real subprocess chain is ever reached, so it carries zero test coverage today on either side. Also flagged for the Rule-2 closing CFE retrospective as a newly-discovered gotcha in the wrapped tool, since a fix belongs there, not here.
  status: done 2026-08-20 — Story 5.5 (Rule-2 CFE retrospective).
  resolution: fixed in the wrapped tool, as this entry anticipated. `recipe_updater.py`'s real-write path now resolves `os.environ.get("CONDA_PYTHON_EXE") or sys.executable`, mirroring `github_updater.py` exactly. Landed as CFE v8.82.0's gotcha G108.
  guarded by: `.claude/skills/conda-forge-expert/tests/unit/test_recipe_updater_interpreter.py` — one behavioral test that drives the real (non-dry-run) write path end-to-end and asserts the captured `subprocess.run` argv[0] is the resolved interpreter, never the literal string `"python"`; one test asserting `recipe_updater.py` and `github_updater.py` share the identical resolution line.
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — resolved — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to resolved

### DW-2-5-1: `mason recipe validate`'s `EXIT_FAILED` conflates "the recipe failed validation" with "an anticipated Mason-side error occurred"
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-5-mason-recipe-validate.md`
  summary: `recipe validate` is the one verb whose dispatch branch projects the wrapped tool's own pass/fail outcome onto the process exit code (`EXIT_OK`/`EXIT_FAILED`, FR-8) rather than always reporting `EXIT_OK`. But `EXIT_FAILED=1` is the same code every other `MasonError`/unanticipated-exception path already uses, so a CI pipeline gating on this verb's exit code cannot distinguish "the recipe has real lint findings" from "Mason/CFE integration itself broke" (e.g. a `CfeTimeoutError`) -- both land on the identical `1`, even though the module already carves out a dedicated code for a different CFE-related outcome (`EXIT_CFE_UNAVAILABLE=3`).
  evidence: Confirmed by reading `exit_codes.py`'s closed five-code taxonomy (AD-7: "`exit_codes.py` is the sole producer of every exit code... no other module computes or hardcodes one") and `cli.py`'s `recipe`/`validate` branch, which returns `EXIT_FAILED` both for a `CfeTimeoutError`/`MasonError` (via `main()`'s generic handlers) and for a clean subprocess run that simply reported `passed: false`. Raised by adversarial review (Blind Hunter) against the Story 2.5 diff, 2026-08-13. Not this story's defect to fix alone: AD-7's exit-code set is a closed architecture decision, and the spec's own Boundaries & Constraints already considered and accepted this (`Block If: N/A -- FR-8 plus the diagnose()/scan() precedents fully determine the scope`) rather than inventing a new code unilaterally. A proper fix -- a dedicated exit code for "the wrapped tool reported a domain-level failure," distinct from `EXIT_FAILED`'s "Mason itself failed" -- would be an AD-7 amendment affecting the whole exit-code taxonomy, not a single-verb change, so it belongs to a future architecture-level pass, not this story.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-5-2: The hand-maintained verb-registration ordinal comments in `cli.py` (e.g. "the second verb registered", "the third verb registered") have no mechanical guard and will drift as more verbs land out of story-number order
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-5-mason-recipe-validate.md`
  summary: Landing `validate` (Story 2.5) between `new` (2.4) and `build` (2.6) in registration order required hand-editing `build`'s own pre-existing comment from "the second verb registered under any noun" to "the third verb registered under any noun" -- a manual, easy-to-miss bookkeeping step with no test or lint asserting the stated ordinal actually matches the verb's real position in `_noun_verbs["recipe"].choices`.
  evidence: Confirmed while implementing this story: only `recipe build`'s own comment needed correction this pass, but nothing scans `cli.py` to catch a similarly-worded but unedited ordinal elsewhere (e.g. `submit`'s "a fifth verb"/`update`'s "a sixth verb" claims, which were not verified against the actual registration count during this pass since they were outside this story's Code Map). Raised by adversarial review (Blind Hunter) against the Story 2.5 diff, 2026-08-13. Pre-existing pattern across every prior story in this file, not introduced by this one; a proper fix would derive each comment's ordinal from `len(_noun_verbs["recipe"].choices)` at the point of registration (or drop the ordinal claims from prose entirely, since `_noun_verbs["recipe"].metavar`'s own derivation already documents registration order mechanically) rather than hand-counting in comments.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-5-3: No test structurally proves every OTHER `recipe` verb's `cli.py` branch stays `EXIT_OK` regardless of its wrapped tool's own outcome -- the invariant `recipe validate`'s docstrings lean on ("the one exception among every recipe verb") is asserted only in prose
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-5-mason-recipe-validate.md`
  summary: `recipe.py`/`cli.py`'s module docstrings and `validate()`'s own docstring repeatedly claim `recipe validate` is "the one CLI-level exception" to a module-wide rule ("every other verb's branch always returns `EXIT_OK`"), but no test sweeps all six sibling verb branches (`build`/`diagnose`/`optimize`/`scan`/`submit`/`update`) to confirm none of them also project a non-zero wrapped-tool outcome onto the exit code. Only `build` has a positive regression test for this (`test_recipe_build_failed_child_still_renders_ok`); `diagnose`/`optimize`/`scan`/`submit`/`update` have no equivalent, so the claim could silently become false for one of them (today, by inspection, or in a future edit) with nothing to catch it.
  evidence: Confirmed by searching `test_cli.py` for `_still_renders_ok`/`failed_child`-style test names -- only the one `build` test exists. Raised by adversarial review (Blind Hunter) against the Story 2.5 diff, 2026-08-13. A module-wide test-completeness gap predating this story (the five other verbs' `EXIT_OK`-regardless-of-outcome behavior was never pinned by a dedicated test when each landed), only surfaced now because this story's own docstrings are the first to assert the invariant explicitly in prose; a proper fix would add one `..._failed_child_still_renders_ok`-style test per sibling verb, mirroring `build`'s existing one.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-5-4: `cfe.validate_recipe(["--json", recipe_path], ...)` has no `--` separator, so a `recipe_path` beginning with `-` could be misparsed as a flag by the wrapped validator's own `argparse`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-5-mason-recipe-validate.md`
  summary: `validate()` builds argv as `["--json", recipe_path]` with no `--` separator before the positional. A `recipe_path` value starting with `-` (e.g. a path a user constructs as `-recipes/foo` or similar) would be parsed by `validate_recipe.py`'s own `argparse.ArgumentParser` as an unrecognized flag rather than the intended positional path, producing a confusing CFE-side usage error instead of Mason's own clear "recipe not found"-style outcome.
  evidence: Confirmed by reading `validate_recipe.py`'s `argparse` setup directly (a single positional `path` argument with no special dash-handling). Raised by Edge Case Hunter against the Story 2.5 diff, 2026-08-13. Not unique to this story: `cfe.scan_for_vulnerabilities(["--json", recipe_path], ...)` (Story 2.8) already carries the byte-identical exposure, unaddressed there too, so fixing only `validate()` here would create a new, inconsistent precedent rather than close the actual gap. A proper fix -- inserting `"--"` before the positional in both adapters' argv, or in `cfe.py`'s shared `_invoke_captured` for every CAPTURE-mode caller at once -- belongs to a dedicated pass covering both call sites (and auditing any future one) together.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-6-1: `doctor.py`'s per-noun `unavailable_verbs` granularity is now inaccurate for `recipe build`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-6-mason-recipe-build.md`
  summary: `doctor.build_report` marks the whole `"recipe"` noun unavailable whenever the CFE import floor has any gap, but `recipe build` (both `build_native` and `build_docker`) needs no import floor at all, so `mason doctor` can now report `recipe` unavailable while `mason recipe build` actually works fine.
  evidence: Confirmed by reading `doctor.py`'s own docstring/logic (`unavailable_verbs = ("recipe",)` set from `resolved_root.step == STEP_NOT_FOUND or floor_result.missing`, with no per-verb distinction) against `recipe.py`'s Story 2.6 module docstring, which states plainly that neither wrapped build script depends on CFE's Python import floor. Pre-existing, coarse per-noun-not-per-verb granularity from Story 1.8, written before any `recipe` verb existed; fixing it properly is a doctor.py design question (whether/how to go per-verb) out of proportion for this story to redesign unilaterally. Raised independently by both review passes (Blind Hunter adversarial review) against the Story 2.6 diff, 2026-08-12.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-7-1: A malformed `MASON_CFE_TIMEOUT` environment value is silently ignored with no warning
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-7-mason-recipe-diagnose.md`
  summary: `cli.py::_resolve_optional_float` (shared, shipped in Story 1.10) falls back to `None` for any unparseable/non-finite/non-positive `MASON_CFE_TIMEOUT` value with no warning logged, even though `_configure_logging` has already run by the time this resolves -- `--cfe-timeout` itself cannot hit this path (argparse's `_parse_finite_float` validates it first), but the environment half of the same knob has no equivalent guard.
  evidence: Confirmed by direct inspection of `_resolve_optional_float`'s docstring and body (every failure mode -- unset, whitespace-only, unparseable, non-finite, non-positive -- "fall back to `None` rather than raising"). Pre-existing behavior of already-shipped, unchanged code; Story 2.7 (`recipe diagnose`) is simply the first real caller that exercises this environment-variable path in practice (previously the helper existed but nothing in `main()` called it). Raised by adversarial review against the Story 2.7 diff, 2026-08-12. A proper fix (e.g. a one-line warning log on fallback) belongs to `_resolve_optional_float` itself, benefiting every future `--cfe-timeout` consumer, not a `recipe diagnose`-local workaround.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-7-2: `mason package`/`mason environment` still print the literal `{}` token for an invalid verb
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-7-mason-recipe-diagnose.md`
  summary: Story 2.7's own review pass fixed `recipe`'s verb-subparsers action so its `metavar` is derived from `.choices` after `diagnose` is registered (`mason recipe <bad-verb>` now shows `{diagnose}`), but `package`/`environment` still have zero registered verbs and their captured `_noun_verbs["package"]`/`["environment"]` actions keep the original literal `metavar="{}"` set in `build_parser()`'s per-noun loop, so `mason package <any-verb>`/`mason environment <any-verb>` still print the bare `{}` token instead of an accurate choice set.
  evidence: Reproduced live: `mason package bogus-verb` prints `mason package: error: argument {}: invalid choice: 'bogus-verb' (choose from )` -- the identical cosmetic defect class Story 2.7's review pass named and fixed for `recipe`, left unfixed for the two sibling nouns because this story's scope only registers a `recipe` verb. Pre-existing since Story 1.2 (`build_parser()`'s original per-noun loop hardcoded `metavar="{}"` before any verb existed anywhere), not introduced by this diff; surfaced incidentally by adversarial review against the Story 2.7 diff, 2026-08-12. A proper fix applies the same `.choices`-derived metavar to every noun's captured verb-subparsers action, not just `recipe`'s -- natural to land in whichever future story (2.8+) first registers a verb under `package` or `environment`.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-8-1: `render_text`'s one-line-per-key format double-prints `scan`'s findings, now the largest payload it renders
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-8-mason-recipe-optimize-and-mason-recipe-scan.md`
  summary: `render_text` prints both the raw `stdout`/`stderr` strings and the already-parsed `json_body` as separate top-level keys, so any real `recipe scan` result (vulnerability lists, aliases, summaries across many packages) appears twice in text-format output -- once as an unwrapped JSON blob under `stdout:`, once structured under `json_body:` -- a pre-existing cosmetic wart made considerably more visible now that `scan`'s payloads are likely the largest/noisiest `json_body`s Mason renders yet.
  evidence: Confirmed by reading `render.py`'s `write`/text-rendering path (unchanged by this diff) against the `CfeResult` shape both `optimize()` and `scan()` return -- `dataclasses.asdict(result)` always includes `stdout`/`stderr`/`json_body` as sibling keys, and the text renderer has no special-casing to suppress the raw duplicate once a structured one exists. Pre-existing since Story 2.1 (`validate_recipe`/`submit_pr`/`diagnose_failure` already exhibit the same double-print), not introduced by this diff; raised by adversarial review against the Story 2.8 diff, 2026-08-12. A proper fix belongs to `render.py` itself (e.g. suppress `stdout`/`stderr` in text mode once `json_body` parses successfully), benefiting every existing and future CAPTURE-mode verb, not a `recipe scan`-local workaround.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-8-2: `_OPTIMIZE_RELEVANT_FLOOR`/`_SCAN_RELEVANT_FLOOR` are hand-declared, never derived from or cross-checked against the real wrapped scripts
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-8-mason-recipe-optimize-and-mason-recipe-scan.md`
  summary: `recipe.py`'s `_OPTIMIZE_RELEVANT_FLOOR = ("ruamel.yaml",)` and `_SCAN_RELEVANT_FLOOR = ("pyyaml", "requests")` are literal tuples whose docstrings say "confirmed by reading it," but nothing in the test suite parses the real `recipe_optimizer.py`/`vulnerability_scanner.py` `try/except ImportError` blocks to keep these tuples in sync -- if a future CFE skill change adds (or drops) a third-party import in either script, Mason's per-operation floor gate has no way to notice, and would either wrongly reject a now-satisfiable call or wrongly admit a now-doomed one straight into a subprocess spawn.
  evidence: Confirmed by reading both real scripts directly (`.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py`, `vulnerability_scanner.py`) -- their import sets match the two tuples today, but the match is asserted only in a docstring comment, not enforced by any AST scan or fixture-derived check. Raised by adversarial review against the Story 2.8 diff, 2026-08-12; not this story's own defect (the two-tuple-per-operation design itself is spec'd and correct), but a drift vector affecting whichever future story next touches either wrapped script's import list. A fix would mirror `test_adapter_sole_caller.py`'s existing AST-based style: parse each real script's `try: import X / except ImportError` block and assert the relevant tuple matches exactly.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-9-1: The unparseable-body PENDING fallback in `_ship_target_result_from_cfe_result` carries no reference or message
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-9-mason-recipe-submit.md`
  summary: When `confirm=True`, `json_body` fails to parse as a dict, and `result.returncode == 0`, the state-mapping helper returns `ShipTargetResult(state=PENDING, reference=None, message=None)` -- a "pending" outcome with nothing attached to explain why, even though AD-10's own quoted principle ("if a target cannot be interrogated, the result is pending with the reason") the same docstring cites elsewhere implies a reason should accompany it.
  evidence: Confirmed by reading `_ship_target_result_from_cfe_result` directly and by the parametrized test added this pass (`test_submit_confirmed_unparseable_body_falls_back_to_returncode`), which pins the current (message=None) shape rather than fixing it. Low real-world likelihood: `submit_pr.py`'s own `main()` always `print(json.dumps(result, indent=2))`s its full result body before `sys.exit`, so a genuinely unparseable stdout with `returncode == 0` requires a malformed/patched wrapped script, not normal operation -- this fallback exists as a defensive branch, not a reachable path today. Raised by adversarial review (Blind Hunter) against the Story 2.9 diff, 2026-08-12. A proper fix would likely attach `result.stdout`/`result.stderr` (truncated) as `message` in this one fallback branch so a genuinely broken wrapped script's output isn't silently discarded -- deferred rather than patched inline because it touches the same helper the `message` falsy-fallback fix (this pass) already changed, and widening `message`'s source (from JSON-body-only to raw-stdout-fallback) is a small but real behavioral decision better made deliberately than folded into an unrelated triage pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-1-1: `CfeImportFloorError` lacks a `__reduce__` override, so `deepcopy`/`pickle` corrupt its `.args`/`repr()` on round-trip -- the same bug class `CfeUnresolvedError`/`CfeTimeoutError` were already fixed for
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-1-engine-protocol-and-provisioning.md`
  summary: `errors.py`'s `CfeImportFloorError(missing, interpreter)` has no `__reduce__` override, unlike its siblings `CfeUnresolvedError`/`CfeTimeoutError`, both of which carry one specifically because `MasonError.__init__` sets `self.args = (identifier, message)`, which does not match either subclass's own constructor signature. `CfeImportFloorError`'s two-positional-argument shape has the identical mismatch, so `copy.deepcopy`/`pickle.loads(pickle.dumps(...))` reconstruct it via `cls(*self.args)` = `CfeImportFloorError("cfe:import-floor-missing", <built message>)`, binding `missing` to a tuple of characters of the identifier string and `interpreter` to the full message string.
  evidence: Verified directly: `copy.deepcopy(CfeImportFloorError(missing=("pyyaml",), interpreter="/opt/py"))` reconstructs via the corrupted call above, then `__dict__` state-restore (the second half of `Exception.__reduce__`'s default 3-tuple) overwrites `.missing`/`.interpreter`/`.message` back to their correct original values -- so `str()`, `.missing`, and `.interpreter` all survive intact, but `.args` itself, and therefore `repr(exc)`, stays permanently garbled with no override. Surfaced incidentally by Story 3.1's adversarial review (Blind Hunter, 2026-08-13), which found and this pass fixed the identical gap in the new `EngineAbsentError` class; `CfeImportFloorError`'s own version of the bug is pre-existing since Story 1.6 and out of this story's scope (`errors.py` predates Story 3.1; only `EngineAbsentError` is this story's own code). A proper fix mirrors `CfeTimeoutError.__reduce__` exactly: return `(self.__class__, (self.missing, self.interpreter))`, plus a `test_cfe_import_floor_error_survives_deepcopy`/`..._survives_pickle_round_trip` pair in `test_errors.py` matching the existing `CfeTimeoutError`/`CfeUnresolvedError` coverage.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-4-1: `ship_pypi` unconditionally builds the `.conda` package too, coupling a PyPI-only ship to conda-side build/version-mismatch failures
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-4-the-pypi-ship-target.md`
  summary: `ship_pypi()` calls `package.py::build()` unconditionally, which (Story 3.2's own established design, unchanged here) always runs both the PEP-517 wheel/sdist engine and the pixi `.conda` engine in one call, and raises `PackageVersionMismatchError`/`EngineAbsentError` for a problem on the CONDA side even when a user only wants to ship to PyPI. A project where `pixi` is absent from `PATH`, or whose conda-side manifest is broken, cannot ship to PyPI alone via `ship_pypi` even though nothing about the PyPI half is broken.
  evidence: Confirmed by reading `package.py::build()` (Story 3.2, unchanged by this diff): both `pep517.build()` and `pixi.build()` run unconditionally and in sequence, and a version disagreement between the two raises `PackageVersionMismatchError` before either artifact path is returned. `ship_pypi`'s own spec (Design Notes) explicitly reuses `build()` "unconditionally... FR-15, reused not duplicated" per FR-16's own PRD text ("ship builds first... reusing FR-15's implementation rather than duplicating it") -- this coupling is Story 3.2's pre-existing, already-shipped design, not something Story 3.4 introduced. Raised by adversarial review (Blind Hunter) against the Story 3.4 diff, 2026-08-13. Whether a version mismatch SHOULD block a PyPI-only ship is arguably intentional (epic-3-context Requirements: "Before any upload, wheel version and conda-package version are compared; a mismatch aborts showing both values" -- a cross-ecosystem consistency check, deliberately not scoped per-target), but an `EngineAbsentError` for the CONDA engine specifically blocking a PyPI-only ship has no such stated rationale and is a genuine target-isolation gap. A proper fix belongs to Story 3.9 (the multi-target `ship` orchestrator) or a `build()` redesign separating "build wheel/sdist" from "build .conda" so a single-target ship requests only what it needs -- out of scope for this story, which FR-16 requires to reuse `build()` as-is.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-5-1: `engines.pixi.upload()`'s argv has no `--` separator, so a `channel_name` (or `conda_path`) starting with `-`/`--` is misparsed by pixi's own clap CLI instead of reaching `--channel`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-5-the-channel-name-ship-target.md`
  summary: `upload()` builds `argv = ["pixi", "upload", "prefix", "--channel", channel, conda_path]` with `channel`/`conda_path` as bare values -- nothing stops a `channel_name` beginning with `-` from being parsed by pixi's clap-based CLI as another flag rather than `--channel`'s value. `parse_ship_targets()` (Story 3.3, unchanged here) only requires the channel-name suffix be non-empty after stripping; it does not reject a leading `-`/`--`.
  evidence: Live-verified against the installed `pixi 0.76.2` binary during the 2026-08-13 review pass: `pixi upload prefix --channel -evil fake.conda` fails with clap's own `error: unexpected argument '-e' found` -- a `--ship "channel:-myorg"` invocation would surface as a baffling clap parse error inside a `FAILED` `ShipTargetResult.message`, instead of a clean, named Mason error. Raised independently by both Blind Hunter and Edge Case Hunter across two review passes (2026-08-13) against the Story 3.5 diff. Not blocking: the vocabulary parser already guards non-emptiness, and no CLI wiring exists yet (Story 3.9's scope) to reach this path at all in v1. A proper fix inserts a `--` separator before the trailing positional (`[..., "--channel", channel, "--", conda_path]`, if pixi's clap parser honors it for the final positional) or validates `channel_name`/`conda_path` don't start with `-` before building argv -- belongs to whichever story first wires a real caller (Story 3.9), since no live-verified fix shape was confirmed during this pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-5-2: `engines.pixi.upload()` sets no `stdin=subprocess.DEVNULL`, unlike `twine.py`'s documented interactivity defense -- an unverified risk that `pixi upload prefix` could block on a stdin prompt for the full timeout window
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-5-the-channel-name-ship-target.md`
  summary: `engines/twine.py::upload()`'s own docstring explains its `--non-interactive` flag exists as "defense-in-depth so a spawned child can never block on a stdin prompt." `engines.pixi.upload()` has no equivalent: no flag suppressing interactive prompts, and no `stdin=subprocess.DEVNULL` override on the `subprocess.run` call. If `pixi upload prefix` ever prompts (e.g. an existing-package collision -- the real CLI exposes `--skip-existing`/`--force` flags, neither passed here), the child could consume the entire `_PIXI_UPLOAD_TIMEOUT_SECONDS` window blocked on a read before `subprocess.run`'s own timeout kills it.
  evidence: Raised by Blind Hunter against the Story 3.5 diff, 2026-08-13 review pass 2, by direct comparison to `twine.py`'s own explicit, already-shipped defense against the identical risk class. Not independently live-verified during this pass (would require triggering a real upload collision against a live prefix.dev channel), so whether `pixi upload prefix` actually ever prompts on stdin is unconfirmed -- the risk is real by analogy to `twine`'s documented rationale, not by direct reproduction. A proper fix adds `stdin=subprocess.DEVNULL` to the `subprocess.run` call (cheap, matches `twine.py`'s own defense-in-depth posture even if pixi never actually prompts) after confirming it doesn't interfere with `pixi`'s own credential-prompt fallback path (`pixi auth login`-style interactive auth is explicitly out of Mason's v1 credential-blindness model per this story's own Never boundary, so suppressing stdin entirely should be safe, but wasn't live-verified this pass).
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-6-1: `ship_conda_forge`'s `try/except (OSError, ValueError)` around `Path.expanduser().resolve()` does not catch `RuntimeError`, which `expanduser()` raises when `~` cannot be resolved
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-6-the-conda-forge-ship-target.md`
  summary: `package.py::ship_conda_forge` resolves `recipe_path`, the CFE root, and the expected recipe directory inside one `try: ... except (OSError, ValueError) as exc: return ShipTargetResult(state=FAILED, message=str(exc))` block, matching its own docstring's promise that a pathological path resolves to `FAILED` data rather than crashing. `Path.expanduser()` raises `RuntimeError` (not `OSError`/`ValueError`) when a `~`-prefixed path cannot be resolved -- most commonly when `HOME` is unset in the process environment -- so that specific failure mode is not caught and would propagate as a raw, un-typed exception instead of the documented `FAILED` result.
  evidence: Raised by Edge Case Hunter against the Story 3.6 diff, 2026-08-13 review pass. Confirmed by reading `pathlib.Path.expanduser`'s documented behavior and the exact `except (OSError, ValueError)` clause in `ship_conda_forge` (`package.py`). Not patched in this pass: `recipe.py::submit()` (Story 2.9) has the identical, already-shipped gap in its own `recipe_dir = Path(recipe_path).expanduser().resolve()` try/except -- `ship_conda_forge`'s own spec explicitly instructed mirroring that established precedent for this exact resolve-failure mode, so patching only the new copy would diverge from the function it was designed to match, leaving two inconsistent implementations of the same pattern. A proper fix adds `RuntimeError` to both functions' except clauses in the same pass, verifying the resulting message text still reads sensibly for a `HOME`-unset failure (untested territory for either function today).
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-6-2: `resolve_cfe_root` returns flag/environment roots un-expanded and `cfe.py` never expands them, so a `~`-prefixed CFE root reaches every child-process invocation as a literal path that cannot exist
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-6-the-conda-forge-ship-target.md`
  summary: `resolve.py::resolve_cfe_root`'s flag and environment steps return `Path(explicit.strip())` / `Path(env_value.strip())` verbatim, with no `.expanduser()`, and `cfe.py::_invoke_captured` composes the CFE script path straight off that raw value (`script_path = root / ".claude" / "scripts" / "conda-forge-expert" / ...`). Nothing between resolution and the subprocess ever expands `~`. A `MASON_CFE_ROOT=~/my-cfe` (or a quoted `--cfe-root "~/my-cfe"`) therefore produces a literal `~/my-cfe/.claude/scripts/conda-forge-expert/submit_pr.py`, which no filesystem resolves — so every CFE-backed verb fails with an opaque child-process error rather than a named Mason error. Story 3.6's two new call sites (`package.py::ship_conda_forge` and `doctor.py::build_report`) are the only places in the package that expand a root at all, which makes the inconsistency newly visible: `mason doctor` now affirmatively reports `conda_forge_ship_ready=True`, zero blockers, for a root that cannot ship, and `ship_conda_forge`'s location precondition likewise passes before handing the same unusable root to `recipe.submit()`.
  evidence: Reproduced during the 2026-08-13 follow-up review pass (Blind Hunter) against a real temporary `HOME`: `build_report(cfe_root_arg="~/mycfe", ...)` returned `cfe_root='~/mycfe'`, `conda_forge_ship_ready=True`, `conda_forge_ship_blockers=()`, while the path `cfe.py` would build from that same root (`~/mycfe/.claude/scripts/conda-forge-expert/submit_pr.py`) does not exist. Confirmed by reading `resolve.py::resolve_cfe_root` (both early-return steps construct a bare `Path` with no expansion; only the walk step produces an already-resolved path) and `cfe.py:827` (raw `root` used to compose `script_path`); `grep -rn expanduser src/` shows the CFE root is expanded in exactly two places package-wide, both added by the Story 3.6 diff. Note this is a PRE-EXISTING, whole-package defect, not one this story introduced: every CFE-backed verb (`mason recipe build/diagnose/optimize/scan/submit/update`) has failed this way since the resolution chain shipped, and it also affects the single-field consistency of `DoctorReport`, whose `cfe_root` is rendered un-expanded while the new readiness fields are computed against the expanded form. Not patched in this pass: the correct fix normalizes the root ONCE at resolution (`resolve_cfe_root` returning an expanded/resolved `Path` for its flag and environment steps, matching what its walk step already returns) rather than adding a third independent expansion at each consumer, and that change alters the value every existing `resolve.py` test asserts on plus the `cfe_root` string `mason doctor` prints — a deliberate, separately-verified pass. Deliberately NOT worked around inside `doctor.py` here: removing Story 3.6's expansion would make `doctor` disagree with `ship_conda_forge`'s own identical resolution and would regress the correctly-handled relative-root case, trading a narrow false positive for a broader false negative.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-6-3: `resolve_cfe_root`'s unguarded `start_directory.resolve()` sits outside every caller's `try`, so a deleted process cwd makes both `doctor.build_report` and `package.ship_conda_forge` raise `FileNotFoundError`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-6-the-conda-forge-ship-target.md`
  summary: `resolve.py::resolve_cfe_root`'s cwd-walk step opens with a bare `candidate = start_directory.resolve()` (no `try`). Both of its Story 3.6-relevant callers guard everything *after* that call but nothing *around* it: `doctor.py::build_report` calls it as its first statement, above all of pass 1's and pass 2's `except (OSError, ValueError, RuntimeError)` hardening, and `package.py::ship_conda_forge` calls it before entering its own `try`. When `start_directory` is relative (the production shape -- `cli.py` passes `Path.cwd()`) and the process's working directory has been deleted, `.resolve()` raises `FileNotFoundError`, which escapes both functions -- breaking `build_report`'s documented "Never raises" invariant and `ship_conda_forge`'s docstring promise that a resolve failure returns `ShipTargetResult(FAILED)` rather than raising. Only reachable when the flag and environment steps do not short-circuit first (no `--cfe-root`, no `MASON_CFE_ROOT`).
  evidence: Reproduced during the 2026-08-13 follow-up review pass (raised by Blind Hunter, confirmed independently): with the process cwd removed via `os.chdir(d); os.rmdir(d)`, both `doctor.build_report(None, None, {}, Path("."))` and `package.ship_conda_forge("recipes/foo", environ={}, cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None, start_directory=Path("."))` raised `FileNotFoundError: [Errno 2] No such file or directory`. PRE-EXISTING, not introduced by this story: `git diff` over the Story 3.6 range shows `resolve.py` is untouched (0 lines changed), and `build_report` already called `resolve_cfe_root` as its first statement before this story -- the spec's own Code Map describes the new fields as "computed from the `resolved_root` `build_report` already has". Story 3.6 only makes the exposure easier to notice, because two review passes hardened the code immediately below this call while the call itself stayed bare. Not patched in this pass: the fix belongs in `resolve.py` (guarding the walk's own `.resolve()` and deciding what a resolution-failed walk returns -- most likely `STEP_NOT_FOUND`, which is a behavior decision affecting every `resolve.py` consumer and every `resolve.py` test), not in a third independent per-caller `try` that would leave the other CFE-backed verbs still exposed. Adjacent to but distinct from `DW-3-6-2`: that entry concerns the CFE ROOT being returned un-expanded, this one concerns the START DIRECTORY resolution raising; both point at `resolve_cfe_root` normalization and would sensibly be fixed in one pass.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-7-1: A concurrent ship of the same PyPI/channel name+version between `version_exists`/`pixi.search` returning `False` and the actual `upload()` call reports `FAILED`, not `TERMINAL`, for the loser of the race
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-7-asymmetric-receipts-partial-failure-and-idempotence.md`
  summary: `ship_pypi`/`ship_channel` interrogate their target, and only proceed to `twine.upload`/`pixi.upload` when the interrogation conclusively returns `False` ("not yet shipped"). Between that check and the upload call there is a real, if narrow, window in which a second, concurrent ship of the identical name+version can complete first. The now-late upload then fails on the target's own duplicate-artifact rejection, and this diff's `upload_result.returncode != 0` branch reports that as a plain `FAILED` result -- rather than re-interrogating (or otherwise recognizing) that the artifact is, in fact, now shipped.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter against the Story 3.7 diff, 2026-08-14 review pass (both framed it as a TOCTOU gap between the new interrogation step and the pre-existing upload call). Confirmed by reading `ship_pypi`/`ship_channel`'s own control flow: the `False` branch falls straight through to `twine.upload`/`pixi.upload` with no re-check, and a nonzero `upload()` returncode is unconditionally mapped to `ShipTargetResult(state=FAILED, ...)` (Story 3.4/3.5's own already-shipped precedent, unchanged by this diff). Not this story's defect to fix alone: the ambiguity itself -- "did the upload fail because it already exists, or for a real reason?" -- predates this story (every ship attempt before 3.7 had a 100% chance of hitting it on any retry; 3.7 only narrows the window from "every retry" to "a genuine concurrent race"). A proper fix would need to distinguish a duplicate-artifact rejection from any other upload failure in `upload_result.stdout` (twine's and pixi's own wording for that specific rejection would need to be identified and pattern-matched, mirroring `engines.pixi.search`'s own `"No packages found"` substring technique) and remap that one case to `TERMINAL` -- a change to `engines.twine.upload`/`engines.pixi.upload`'s own result classification, not a `package.py`-only patch, and out of this story's scope.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-7-2: `pypi_index.version_exists` always queries the public `pypi.org` index, even when the caller's own environment points `twine` at a different repository via `TWINE_REPOSITORY_URL`
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-7-asymmetric-receipts-partial-failure-and-idempotence.md`
  summary: `ship_pypi`'s new interrogation step calls `pypi_index.version_exists()`, which is hardcoded to `GET https://pypi.org/pypi/<name>/<version>/json` (spec Always boundary). `engines.twine.upload()` passes no `env=` override to `subprocess.run` (AD-14: the child inherits the caller's full environment unchanged), so `twine` itself will honor a `TWINE_REPOSITORY_URL`/`TWINE_REPOSITORY` value from that inherited environment if the user has one set -- meaning the interrogation and the actual upload target can silently diverge for any user shipping to a private index (e.g. an internal Artifactory/devpi mirror) rather than public PyPI.
  evidence: Raised by Edge Case Hunter against the Story 3.7 diff, 2026-08-14 review pass. Confirmed by reading `pypi_index.py` (the URL template is a fixed, non-configurable module constant) and `engines/twine.py::upload()` (no `env=` kwarg is ever passed, so `TWINE_REPOSITORY_URL` reaches the child exactly as `twine` itself would honor it outside Mason entirely). Not addressed by this story: no repository-selection knob exists anywhere in this branch's `ship_pypi`/`twine.upload` yet either (Story 3.9's `repository_url` parameter, added in a sibling not-yet-merged worktree, is the first place any such knob lands, and even that is a hardcoded TestPyPI constant, not a `TWINE_REPOSITORY_URL`-aware read) -- `pypi_index.py`'s own scope (module docstring, spec Intent) is explicitly "PyPI's own public JSON index," matching FR-20's framing that Mason relies on "the standard environment variables the chosen uploader honours" rather than modeling repository selection itself. The consequence is bounded, not silent corruption: a false "already shipped" skip is possible only if the exact name+version coincidentally already exists on public PyPI while absent from the private index; a false "not yet shipped" proceed-to-upload is also bounded, since the private index's own duplicate-rejection (if any) still applies. A proper fix would need `pypi_index.version_exists` to accept (or independently derive) the same repository URL `twine` will actually use, which does not exist as a readable/derivable value anywhere in this package today -- belongs to whichever future story first makes repository selection a first-class Mason concern.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-7-3: `ship_pypi`'s idempotence check derives package identity from the wheel filename only, never cross-validated against the sdist filename, so a mismatched wheel/sdist pair in a dirty `dist/` could have its skip-or-upload decision made against the wrong project's PyPI listing
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-7-asymmetric-receipts-partial-failure-and-idempotence.md`
  summary: `ship_pypi` derives `pypi_name`/`version` for its new `pypi_index.version_exists()` interrogation solely from `build_result.wheel_path`'s own filename (`parse_wheel_filename`). It never cross-checks that `build_result.sdist_path`'s filename names the same project/version, even though both files are uploaded together in the same `twine.upload((wheel_path, sdist_path))` call two branches later. If `engines.pep517`'s own `_newest()`-based discovery (picking the most-recently-modified matching file in `dist/`) ever selects a wheel and an sdist from two different builds/projects left in a dirty output directory, the interrogation would check one project's identity while uploading a mismatched pair.
  evidence: Raised by Edge Case Hunter against the Story 3.7 diff, 2026-08-14 review pass. Confirmed by reading `ship_pypi`'s new interrogation code (`parse_wheel_filename(Path(build_result.wheel_path).name)` only; `sdist_path` is never parsed or compared) and `engines/pep517.py::_newest` (selects independently, per-glob, by modification time, with no cross-artifact identity check of its own). Pre-existing, not introduced by this story: the underlying risk -- `dist/` holding artifacts from unrelated builds -- is `engines.pep517`'s own established discovery behavior since Story 3.2, and predates any identity-sensitive consumer of `wheel_path`/`sdist_path` together; Story 3.7 is only the first caller to make a DECISION (skip vs. upload) that depends on the wheel's identity matching the sdist's. A proper fix belongs with `engines.pep517.build()` itself -- either validating both discovered artifacts name the same project+version before returning a `PackageBuildResult` at all, or exposing both names so a consumer like `ship_pypi` can cross-check -- rather than a `package.py`-only patch that would only close the gap for this one new caller and leave `twine.upload`'s own silent accept-mismatched-pair behavior unaddressed everywhere else.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-8-1: the `pyforge-mason-test-slow` pixi task's own description text is stale, understating the slow suite it actually runs
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-8-mason-ships-mason.md`
  summary: root `pixi.toml`'s `[feature.pyforge-mason.tasks.pyforge-mason-test-slow]` description reads "collects zero tests until Story 5.3 lands FR-46's delegation-fidelity test" -- already false once Story 3.2 landed `tests/integration/test_package_build.py` (the first real `@pytest.mark.slow` test), and now doubly inaccurate with this story's own second slow test (`tests/integration/test_package_ship.py`) added alongside it.
  evidence: Raised by Blind Hunter against the Story 3.8 diff, 2026-08-14 review pass. Confirmed by reading `pixi.toml`'s task description text directly against `pixi run -e pyforge-mason pyforge-mason-test-slow`'s actual output (`2 passed, 1385 deselected`, both real, non-mocked self-hosting tests). Not this story's defect to fix alone: the description first went stale when Story 3.2 landed the first slow test, predating this story entirely -- Story 3.8 only makes the drift worse by adding a second slow test on top of an already-inaccurate description. A proper fix is a one-line `pixi.toml` description edit (e.g. naming the actual self-hosting build+ship proof tests it runs) -- mechanical, but out of this story's own disclosed scope (its Never boundary explicitly excludes any change outside the one new test file), and belongs with whichever future pass next touches this task block.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-3-9-1: the FR-24/FR-50 TestPyPI rehearsal gate validates an artifact that is not provably the same bytes later uploaded to `pypi`, since the rehearsal and the real upload each call `build()` independently
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-3-9-the-ship-verb-and-testpypi-rehearsal.md`
  summary: `package.py::ship()`'s FR-24/FR-50/AD-26 rehearsal gate runs a `pypi-test` target to `terminal` before allowing a same-invocation `pypi` target to run for real, but both calls go through `ship_pypi()`, which (per Story 3.4's own already-shipped, explicitly-reasoned design, reaffirmed by this story) calls `build()` independently each time rather than sharing one `PackageBuildResult`. For a project with a fully reproducible build (Mason's own `hatchling`-backed, static-version self-hosting case, SM-1) the two builds are byte-identical and this is moot. For a project whose build is not reproducible across two calls within one invocation (VCS-derived dynamic versioning such as `setuptools-scm`, an embedded build timestamp, or a source edit mid-run), the rehearsal could pass while validating an artifact that differs from the one later uploaded to the real, irreversible PyPI index -- undermining FR-50's own stated purpose ("a rehearsal before an irreversible publish").
  evidence: Raised by Blind Hunter against the Story 3.9 diff, review pass 3 (2026-08-13/14). Confirmed by reading `ship()`'s own per-target dispatch (`_ship_one`, calling `ship_pypi` once for the `PYPI_TEST` target and again, independently, for the `PYPI` target) and `ship_pypi`'s own docstring, which explicitly documents that it owns its own `build()` call per invocation rather than accepting an already-built `PackageBuildResult` (Story 3.4's Design Notes: "Story 3.9's multi-target orchestrator may later call `ship_pypi` once per `--to pypi`... accepting the minor redundancy of `build()` re-running per target... or refactor to share one `PackageBuildResult` -- that composition choice belongs to 3.9"). Story 3.9 explicitly chose the "accept the redundancy" branch of that already-anticipated fork (this story's own spec Always boundary and pass-1 KEEP instructions both reaffirm it), so this gap is a direct, foreseen consequence of that choice, not a new defect this story introduced by omission. Not patched in this pass: properly closing it means building once and sharing the SAME `PackageBuildResult` between the rehearsal and real-ship calls for a `pypi`/`pypi-test` pair specifically -- a real design change to `ship_pypi`'s own signature/contract, reopening a decision Story 3.4 and Story 3.9 have now both independently and explicitly made in the opposite direction. A proper fix should be scoped as its own follow-up (likely landing alongside Story 3.8, "Mason ships Mason," which is the first story that actually exercises this exact `pypi-test` -> `pypi` sequence for real) rather than reopened unilaterally inside a review-pass patch.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-1-1: The `__reduce__`-plus-explanatory-comment boilerplate for deepcopy/pickle round-trip safety is now hand-duplicated across roughly a dozen `MasonError` subclasses, with `EnvironmentLockTimeoutError` simply the newest instance
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-1-lock-engine-adapter-and-provenance.md`
  summary: Every `MasonError` subclass whose constructor takes different arguments than `(identifier, message)` needs its own `__reduce__` override (since `Exception.__reduce__` reconstructs via `cls(*self.args)`, and `MasonError.__init__` always sets `self.args = (identifier, message)` -- the wrong values for a subclass's own constructor). `errors.py` currently hand-writes this override, plus the same multi-line explanatory comment, separately in `CfeImportFloorError`, `CfeUnresolvedError`, `CfeTimeoutError`, `EngineAbsentError`, `PackageVersionMismatchError`, `PackageBuildTimeoutError`, `PackageProjectPathError`, `InvalidShipTargetError`, `ShipCredentialMissingError`, `ShipUploadTimeoutError`, `ShipChannelCredentialMissingError`, `ShipChannelUploadTimeoutError`, and now `EnvironmentLockTimeoutError` -- one more copy of an already many-times-repeated pattern.
  evidence: Raised by Blind Hunter against the Story 4.1 diff, 2026-08-14 review pass. Confirmed by reading every `MasonError` subclass in `errors.py`: each one's `__reduce__` body differs only in which stored attributes it returns as the reconstruction tuple, and each carries a near-identical comment explaining why the override exists. Not this story's defect to fix alone: the duplication predates this story by many stories (the first several subclasses already established the copy-paste pattern), and `EnvironmentLockTimeoutError` was deliberately written to mirror `ShipUploadTimeoutError`'s exact shape per this story's own spec instruction, matching established convention rather than introducing a new one. A proper fix (e.g. a small mixin or a `MasonError.__reduce__` default that introspects `__init__`'s own signature against stored attributes of the same name) would touch all ~12 existing classes at once -- a repo-wide `errors.py` refactor outside any single story's surgical scope, and risks subtly changing pickling behavior for already-shipped, already-tested exception classes if the introspection doesn't exactly match each one's existing stored-attribute-to-constructor-argument mapping.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-3-1: `mason environment lock --help` still advertises `--cfe-root`/`--cfe-python`/`--cfe-timeout`, three flags that are silently meaningless for a command whose own help text declares it "CFE-independent"
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-3-mason-environment-lock.md`
  summary: `environment_lock_parser` is registered with `parents=[global_flags]` (mirroring `package build`'s own registration shape, needed so a global flag given after the verb and its positionals still parses), and `global_flags` bundles the three CFE-resolution flags alongside the genuinely shared ones (`--format`, `--verbose`, `--quiet`). `mason environment lock --help` therefore lists `--cfe-root`/`--cfe-python`/`--cfe-timeout` in its usage even though `environment.lock()` never reads any of them -- a user has no way to know from `--help` alone that three of its documented flags do nothing for this verb.
  evidence: Raised by Blind Hunter against the Story 4.3 diff, 2026-08-14 review pass. Confirmed by reading `_build_global_flags_parser`'s own flag set and `environment_lock_parser = _noun_verbs["environment"].add_parser("lock", ..., parents=[global_flags])`. Not this story's defect to fix alone: `package build` (Story 3.2) already has the identical characteristic -- it too is CFE-independent (spec Always boundary, unchanged by this diff) and registered with the same `parents=[global_flags]` shape, so the confusing help output already existed for at least one verb before this story added a second. A proper fix needs a `global_flags`-parent split (a CFE-flags-bearing parent and a CFE-flag-free parent, with each CFE-independent verb -- `package build`, now also `environment lock` -- using the latter) rather than a per-verb patch, since patching only `environment lock`'s registration would leave `package build`'s identical gap unaddressed and introduce an inconsistency between the two CFE-independent verbs' own help text. Belongs with whichever future story next revisits `cli.py`'s global-flags parent structure.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-1: `mason environment check` should default to the lockfile's own `metadata.platforms` when `--platform` is omitted, because conda-lock's own default is four platforms and checking a narrower lockfile without repeating its subset reports a false `stale=True` after an unrequested network solve
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `mason environment check` should default to the lockfile's own `metadata.platforms` when `--platform` is omitted, because conda-lock's own default is four platforms and checking a narrower lockfile without repeating its subset reports a false `stale=True` after an unrequested network solve.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter against the Story 4.4 diff, 2026-08-15 second review pass, then verified live against the installed `conda-lock` 4.0.2 in this workspace's own pyforge-mason pixi env. Two confirmed facts compose into it: (1) `src_parser/__init__.py:90-95` resolves `platforms` to `list(platform_overrides) if platform_overrides else _parse_platforms_from_srcs(src_files)` and falls back to `DEFAULT_PLATFORMS` (`src_parser/__init__.py:22` -- `["linux-64", "osx-arm64", "osx-64", "win-64"]`, FOUR platforms, not the single "default platform" the spec's I/O matrix assumes) whenever neither `-p` nor the manifests name any; (2) `conda_lock.py:404-415` appends every platform satisfying `platform not in platforms_already_locked` to `platforms_to_lock` REGARDLESS of `--check-input-hash`, and `conda_lock.py:429-470` then runs a real `create_lockfile_from_spec` solve and merge for them. So `mason environment lock env.yml -o lock.yml --platform linux-64` followed by `mason environment check env.yml -l lock.yml` (the subset omitted) solves three uncovered platforms over the network and returns `stale=True` for manifests that never changed. NOT patched in this pass because the fix is a contract change, not an implementation fix: the spec's `<intent-contract>` Always boundary mandates the current behavior verbatim ("`--platform` ... omitted -> `()` -> conda-lock's own default platform applies (never invented by Mason)"), and its I/O matrix carries a matching row asserting "No error expected" -- both inside the frozen intent contract this workflow may not amend. Story 4.3's own 2026-08-14 review pass separately accepted the no-enforced-relationship-with-`lock` posture for `environment lock`, so changing it for `check` alone is a deliberate product decision about whether a staleness gate may read platform scope out of the artifact it is verifying. What WAS patched: `condalock.check()`'s docstring, `_ENVIRONMENT_CHECK_HELP`, the `--platform` flag help, and the spec's Design Notes now state the real four-platform default and instruct the caller to pass the same platforms the lockfile was locked with, so the footgun is documented rather than silent.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-2: every `engines.condalock.check()` test mocks `subprocess.run` against a fixture that real conda-lock would reject, so the suite proves only the tautology "if the temp copy's parsed hash changes, `stale` is True" and never that conda-lock actually rewrites it
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: Every `engines.condalock.check()` test mocks `subprocess.run` against a fixture that real conda-lock would reject, so the suite proves only the tautology "if the temp copy's parsed hash changes, `stale` is True" and never that conda-lock actually rewrites it.
  evidence: Raised by Blind Hunter against the Story 4.4 diff, 2026-08-15 second review pass. Confirmed by reading `tests/unit/test_engines_condalock.py`: all `check()` tests patch `pyforge.mason.engines.condalock.subprocess.run`, and the shared `_write_lockfile` fixture emits only `{"metadata": {"content_hash": ...}}` -- a document conda-lock's own `parse_conda_lock_file` would reject outright for lacking `version` and `package`. The staleness verdict is therefore asserted only against a side effect the test itself performs, never against conda-lock's real write behavior. This matters more than usual here because the write behavior is exactly what this review pass found the code's own docstrings had described incorrectly (the write is inside the `else:` of `if not platforms_to_lock:`, not unconditional) -- a defect a single real round-trip would have caught and a mocked suite structurally cannot. NOT patched in this pass: the mocking is the engine layer's established, spec-sanctioned convention (AD-16, stated in the test module's own docstring, and `lock()`'s own tests are built the same way), so the gap is structural rather than introduced by this story, and closing it means adding real opt-in integration coverage rather than editing these tests. The materials are already in place -- conda-lock 4.0.2 is a run-dependency present in the pyforge-mason pixi env, `tests/integration/` already exists, and `pixi run -e pyforge-mason pyforge-mason-test-slow` already runs `@pytest.mark.slow` tests -- so one round-trip test (lock a trivial manifest, check it clean, mutate the manifest, check it stale, assert the original file's bytes are unchanged throughout) would cover it.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-3: `mason environment check --format json` reports `status: "ok"` with an empty `errors` array even when the conda-lock subprocess itself failed, and `stderr` is inherited rather than captured, so the failure's own diagnostic never enters the JSON document
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `mason environment check --format json` reports `status: "ok"` with an empty `errors` array even when the conda-lock subprocess itself failed, and `stderr` is inherited rather than captured, so the failure's own diagnostic never enters the JSON document.
  evidence: Raised independently by Blind Hunter and Edge Case Hunter against the Story 4.4 diff, 2026-08-15 second review pass. Confirmed by reading `cli.py`'s dispatch branch: `render.write(fmt, sys.stdout, "environment check", "ok", dataclasses.asdict(result), [])` hardcodes both the `"ok"` status and the empty error list, while `condalock.check()` passes `stderr=None` to `subprocess.run`, so conda-lock's own diagnostics go to the inherited terminal and are absent from `CheckResult.stdout`. A `--format json` CI consumer parsing a failed run sees `status: "ok"`, `errors: []`, `stale: false`, `stdout: ""` and a non-zero `returncode`. The exit code IS correct (the prior review pass added the `result.returncode == 0` conjunct, so a failed check exits non-zero), and `returncode` IS present in `data`, so the information needed to distinguish "regenerate your lockfile" from "the solver had no network" is technically machine-readable -- which is why this is a deferral rather than a bug. NOT patched in this pass because both halves are spec-constrained: the `"ok"` status is what the spec's I/O matrix mandates for the stale row and what the codebase's every other dispatch branch does for a Mason-successful invocation (AD-9's "the exit code carries the delegated verdict, not this field"), and the `stderr=None` kwarg is mandated verbatim by the spec's own task list ("`subprocess.run` mirrors `lock()`'s exact kwargs"). Resolving it well means deciding, at the render layer rather than in this one verb, how a wrapped tool's own failure should surface in the JSON envelope -- and would apply equally to `recipe validate` and `package build`, which have the same characteristic today.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-4-4-4: Story 4.4's spec (`spec-4-4-mason-environment-check.md`) has not been promoted from gitignored `implementation-artifacts/` into the tracked `planning-artifacts/specs/` directory, matching a gap already present for Stories 4.1-4.3
- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: CLAUDE.md's "Story specs are durable (tracked), NOT Tier-3" convention requires promoting a story spec into `planning-artifacts/specs/` and committing it there once the story merges, but Story 4.4 (like 4.1, 4.2, and 4.3 before it) still lives only under gitignored `implementation-artifacts/`.
  evidence: Raised by Blind Hunter against the Story 4.4 verification-repair diff, 2026-08-15. Confirmed by listing `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/`: only Epic 1's ten story specs (`spec-1-1-...` through `spec-1-10-...`) are present, per that directory's own `README.md` ("Status (2026-08-10, Phase 1 audit): all 10 done stories (Epic 1 complete; Epics 2-5 backlog, 28 stories) have a spec here"). Epic 4's stories have no tracked spec despite S-4.1/S-4.3/S-4.4 already being landed per this Spec's own `.memlog.md`. NOT patched in this pass: this is a pre-existing, systemic gap spanning all of Epic 4 (and likely 2-3), not something Story 4.4 introduced alone -- promoting only 4.4 in isolation would leave 4.1-4.3 inconsistently behind and risks re-deriving the wrong boundary (the prior "Phase 1 audit" promoted Epic 1 as one batch, not story-by-story). Belongs with a dedicated promotion sweep covering every unpromoted Epic 2-5 story spec at once, the same shape as the 2026-08-10 Epic 1 audit.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (already carried its final id there) during the pre-shutdown deferred-work audit.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-1-10-2: Follow-up review still recommended for 1-10-configuration-surface-logging-and-child-output-streaming after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260809-231234-a3cb; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-2-3-2: Follow-up review still recommended for 2-3-credential-isolation after the damping cap was spent
  origin: review-budget-followup
  source_spec: `spec-2-3-credential-isolation.md`
  severity: low
  reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-193147-b96d; this entry preserves the lingering recommendation for a deliberate later review.
  status: open

  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-3` there, review-budget-followup) during the pre-shutdown deferred-work audit, pass 2.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-5-5-1: The ~26 correct-but-duplicated `_get_data_dir()`/`REPO_ROOT` copies Story 5.5 deliberately left un-migrated to the new shared `scripts/_paths.py` helper have no tracked follow-up or drift guard
- source_spec: `_bmad-output/implementation-artifacts/spec-5-5-rule-2-conda-forge-expert-retrospective.md`
  summary: Story 5.5's own spec explicitly scoped the `_paths.py` migration to the four confirmed-wrong call sites only ("Never: mass-migrate the ~26 other correct-but-duplicated copies... disproportionate blast radius for a closing-retro commit"), and `SKILL.md`'s new constraint says to "migrate them opportunistically when you're already touching that file" — but nothing enforces that opportunistic migration ever actually happens; no lint/grep guard flags a still-hand-rolled parent-walk, and this deferral itself was untracked until this entry.
  evidence: Raised by adversarial review (Blind Hunter) against the Story 5.5 diff, 2026-08-20 — noted the precedent this codebase already has for exactly this shape of consolidation, `_path_guard.py` (AUD-CFE-001/002/006's remediation), which DID get a dedicated meta-test (`test_skill_files_tracked.py`-style enforcement) rather than relying on "migrate opportunistically" alone. Not this story's fix to make (the spec's own Never boundary forbids mass-migrating in this pass, for good reason — the ~26 copies are correct, not broken, and touching all of them would be disproportionate churn for a closing retrospective); a proper fix is a lightweight meta-test asserting no `scripts/*.py` NEW file hand-rolls a `Path(__file__).resolve().parents[N] / "data" / "conda-forge-expert"`-shaped expression instead of importing `_paths`, mirroring how `test_skill_files_tracked.py` enforces a different repo-hygiene rule by walking the filesystem rather than trusting convention.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-FU-5-5: Follow-up review still recommended for 5-5-rule-2-conda-forge-expert-retrospective after the damping cap was spent

- source_spec: `spec-5-5-rule-2-conda-forge-expert-retrospective.md`
  summary: Follow-up review still recommended for 5-5-rule-2-conda-forge-expert-retrospective after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260820-140534-3fbe; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-20 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-6` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-6`.
  severity: low
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-5-4-1: SM-4 (free inheritance) recorded provisionally against v8.82.0 — re-confirm at the next organic CFE MINOR

- source_spec: `epics.md` § Story 5.4 (SM-4 satisfaction record, 2026-08-21)
  summary: Story 5.4 closed using CFE v8.82.0 (2026-08-20) as the "MINOR landing after Mason ships" — but that MINOR was produced by Mason's own closing retrospective (Story 5.5), not an unrelated effort, and the live python_min floor (3.10) currently coincides with the pre-fix hardcoded fallback, so the verb-level output delta is not yet observable. The resolution-layer A/B (old parents[3] never finds the pinning file; new get_repo_root() does) plus a green verb re-run are the recorded evidence.
  evidence: Recorded 2026-08-21 under the operator-chosen hybrid close (record now, re-verify later). Re-confirm when the next CFE MINOR lands from an effort outside Mason's own chain (cadence: v8.79 Jul 18 → v8.80/8.81 Jul 29 → v8.82 Aug 20; the in-flight langflow closure's Rule-2 retro is the likely producer) OR when conda-forge bumps python_min past 3.10, whichever first — re-run `mason recipe optimize` and append the observed verb-level delta to the SM-4 record in epics.md, then close this entry.
  severity: low
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-1-1: symptom_signature tokens are not all meaningfully diagnostic: some rows carry a single generic word (e.g. "fails", "work") or a full sentence pulled verbatim as their entire signature, and common tokens (e.g. "noarch: python", "pip check") repeat across dozens of unrelated rows.

- source_spec: `planning-artifacts/specs/spec-7-1-the-failure-catalog-derives-from-the-skill-spec.md`
  summary: symptom_signature tokens are not all meaningfully diagnostic: some rows carry a single generic word (e.g. "fails", "work") or a full sentence pulled verbatim as their entire signature, and common tokens (e.g. "noarch: python", "pip check") repeat across dozens of unrelated rows.
  evidence: Cross-validated by two independent reviewers (Blind Hunter + the Verification Gap Reviewer) against the real committed catalog: G98's row is just ["fails"] (SKILL.md:3792, an ordinary English word in quotes, not a literal error string); G13 includes "(parens)" and "isolate" (SKILL.md:1814, typographic emphasis, not symptom text); G59 includes an entire reviewer sentence verbatim. Inherent to the deliberately narrow, deterministic quote/backtick extraction rule this story's intent-contract specifies (a pure syntactic derivation, not an NLP/quality filter) — faithful to SKILL.md's prose, not a defect in the extractor. Revisit if/when a consumer (Story 7.2 or a future build-failure matcher) needs stronger signal quality; a fix would need a curated stopword/specificity heuristic that the current spec deliberately doesn't define.
  location: .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:_signature_tokens
  origin: spec-deferred aee7832915ee — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-1-2: The fenced-code-block inclusion heuristic in _symptom_paragraph only fires when the Symptom paragraph's prose ends in a literal colon.

- source_spec: `planning-artifacts/specs/spec-7-1-the-failure-catalog-derives-from-the-skill-spec.md`
  summary: The fenced-code-block inclusion heuristic in _symptom_paragraph only fires when the Symptom paragraph's prose ends in a literal colon.
  evidence: A Symptom paragraph that is a complete sentence (no trailing ':') immediately followed by a diagnostic fenced code block never gets that block's content folded into symptom_signature, even when the block is the most useful diagnostic material in the entry. Empirically grounded in G5's "fails ... with:" pattern (the one case investigated during planning); other, non-colon-ending shapes were not surveyed across all 110 gotchas. Not a defect against any stated AC — all 110 real rows already produce a non-empty signature via the whole-body fallback — but a real, narrow-heuristic limitation worth widening later if signature richness turns out to matter.
  location: .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:_symptom_paragraph
  origin: spec-deferred 3ae0fb0c3b57 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-1-3: _ENFORCED_BY_RE's exact-phrase match ("The optimizer's **CODE** check") has no fallback signal distinguishing "no check exists yet" from "the phrasing drifted."

- source_spec: `planning-artifacts/specs/spec-7-1-the-failure-catalog-derives-from-the-skill-spec.md`
  summary: _ENFORCED_BY_RE's exact-phrase match ("The optimizer's **CODE** check") has no fallback signal distinguishing "no check exists yet" from "the phrasing drifted."
  evidence: This is the intent-contract's own deliberate design (Always: "This is deliberately conservative... a false non-null pointer is strictly worse than an honest null"), so the brittleness itself is intended behavior, not a bug. The gap is narrower: a future SKILL.md rewording of the two existing declarative sentences (G2/G3) — e.g. pluralizing "check" to "checks", or a typo — would silently degrade that row to null with no diagnostic distinguishing it from a genuine "not yet enforced" gotcha. Currently zero near-miss phrasings exist in the real 110-gotcha corpus, so there is no live impact today. Worth a mild warning/logging enhancement later if SKILL.md's phrasing conventions ever drift.
  location: .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:extract_enforced_by
  origin: spec-deferred f475fbe29d6f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-1-4: failure-catalog.yaml has no schema_version/format_version field.

- source_spec: `planning-artifacts/specs/spec-7-1-the-failure-catalog-derives-from-the-skill-spec.md`
  summary: failure-catalog.yaml has no schema_version/format_version field.
  evidence: Raised by the Blind Hunter review. Reasonable forward-looking idea — nothing today consumes the file (Story 7.2, which will build the consuming lint/drift gate, doesn't exist yet), so adding a version field now would be speculative per this repo's Simplicity First principle ("minimum code that solves the problem; nothing speculative"). Revisit when Story 7.2 defines what it actually needs from the catalog's shape.
  location: .claude/skills/conda-forge-expert/config/failure-catalog.yaml
  origin: spec-deferred 59d5d9740e06 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-2-1: _code_present()'s narrow `code="X"`/`code='X'` literal-substring match could miss a check code defined a different way (spaced `code = "X"`, a dict-literal `"code": "X"`, ...), producing a false unresolved-pointer.

- source_spec: `planning-artifacts/specs/spec-7-2-the-pointers-lint-and-the-drift-gates.md`
  summary: _code_present()'s narrow `code="X"`/`code='X'` literal-substring match could miss a check code defined a different way (spaced `code = "X"`, a dict-literal `"code": "X"`, ...), producing a false unresolved-pointer.
  evidence: This mirrors failure_catalog_generator.py's own _REGISTRY_CODE_RE = re.compile(r'code=["\']([A-Z]+-[0-9]+)["\']') narrow-match convention verbatim -- the spec's own Code Map explicitly directs reusing this exact pattern, and Story 7.1's review already accepted the same narrowness for the generator. Not new to this story; a future widening (if a differently-styled check-code definition is ever added to recipe_optimizer.py) is a legitimate backlog item, not a defect here.
  location: scripts/failure_catalog_check.py:_code_present
  origin: spec-deferred 938b3367633e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-2-2: check_drift() decides ordinary drift vs. generator-broke by testing for the literal string "DRIFT DETECTED" in the generator's stderr -- a real but self-detecting coupling to Story 7.1's exact wording.

- source_spec: `planning-artifacts/specs/spec-7-2-the-pointers-lint-and-the-drift-gates.md`
  summary: check_drift() decides ordinary drift vs. generator-broke by testing for the literal string "DRIFT DETECTED" in the generator's stderr -- a real but self-detecting coupling to Story 7.1's exact wording.
  evidence: If failure_catalog_generator.py's message text ever changes, test_check_drift_detects_drifted_catalog reds immediately (the test asserts on the finding kind, not the string), so the coupling break surfaces at test time rather than as a silent misclassification in production.
  location: scripts/failure_catalog_check.py:check_drift
  origin: spec-deferred 23eb218e647f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-7-2-3: Nothing in this repo currently makes a detector finding (this one included) or a tests/scripts/ failure literally block a PR -- .github/workflows/detectors.yml is advisory-only by a pre-existing 2026-07-31 operator decision, and tests/scripts/ (including this story's new test file) is not invoked by any GitHub Actions workflow at all.

- source_spec: `planning-artifacts/specs/spec-7-2-the-pointers-lint-and-the-drift-gates.md`
  summary: Nothing in this repo currently makes a detector finding (this one included) or a tests/scripts/ failure literally block a PR -- .github/workflows/detectors.yml is advisory-only by a pre-existing 2026-07-31 operator decision, and tests/scripts/ (including this story's new test file) is not invoked by any GitHub Actions workflow at all.
  evidence: Confirmed via the Intent Alignment Auditor's independent read of every workflow file plus this dispatch's own earlier research: detectors.yml's own header comment states findings surface as warning annotations and "the job itself always succeeds, so a detector finding never blocks a merge"; no workflow references tests/scripts or the pyforge-doctor-scripts-test pixi task. Pre-existing, repo-wide, and explicitly out of scope per this story's own spec ("Never flip .github/workflows/detectors.yml from advisory to a hard gate"). Worth a future dedicated decision, not a defect of this diff.
  location: .github/workflows/detectors.yml
  origin: spec-deferred 95cffdae989f — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-CANOPY-2026-08-24: Canopy five-tier surfaces and event backbone (steward-owned)

- source_spec: `docs/dreams/pyforge-unifying-strategy.md` Phase 5; `planning-artifacts/change-history/sprint-change-proposal-2026-08-24-canopy.md`
  summary: Mason mounts as Canopy station 3. Portal (`/stations/mason/`), MCP face, SKF domain skill (`pyforge-mason`), `Agent-Mason` persona, CloudEvents producer/consumer wiring, and PostgreSQL-first boot reconcile (steward S-25.4) are steward-delivered — not new mason epics beyond Epic 9.
  evidence: Phase-5 `bmad-correct-course` 2026-08-24 (headless-express). Mason Epics 1–9 cover the CLI packaging factory only. Five-tier symmetry gaps (portal, MCP, persona; SKF skill additive to hand-authored CFE) bind to steward Epics 19, 21, 24, 29. MinIO/object-store boot scan is explicitly forbidden for mason (parent AD-1 amended; steward S-25.4: reconcile PostgreSQL + RWX files). `conda-forge-expert` remains hand-authored per canopy AD-17. Liquibase/OpenFeature/cachebox packaging is operator-owned (steward S-26.3), outside mason epic chain.
  location: `_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md` § Canopy obligations (2026-08-24)
  origin: bmad-correct-course Phase 5 headless-express 2026-08-24
  severity: medium
  promoted: 2026-08-24
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 done; mason S-10.1 done (build-engine hook spec; today's engine is default plugin); no competing CI verdict

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

### DW-12-1-1: Guard clause (b) never opens the brief it certifies -- brief_mirrored_through is a pure string equality against tracked YAML, so a re-lost or hollowed-out skill-brief.yaml ships green.

- source_spec: `planning-artifacts/specs/spec-12-1-landed-retros-are-mirrored-into-the-pilot-brief.md`
  summary: Guard clause (b) never opens the brief it certifies -- brief_mirrored_through is a pure string equality against tracked YAML, so a re-lost or hollowed-out skill-brief.yaml ships green.
  evidence: scripts/cfe_rebuild_guard_check.py:223-245 uses brief_path for truthiness only and never reads or stats the file; all 29 tests construct synthetic state dicts; a repo-wide symbol search found no other automated consumer of the brief, and the dual-copy durability arrangement (worktree + main tree) has no ongoing sync check. Natural owner: Story 12.4's clause-(d) detector addition (a runtime-scope check that the brief exists and its amendments name the mirrored SHAs).
  location: scripts/cfe_rebuild_guard_check.py:227
  origin: spec-deferred 611b57d1d425 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-1-2: Slice-1 "equivalence: green" is stale relative to CFE v8.84.0, and guard clause (a) will pass a future compiled->parallel advancement -- the "re-port/re-validate before advancing" gate exists only as prose in next_action.

- source_spec: `planning-artifacts/specs/spec-12-1-landed-retros-are-mirrored-into-the-pilot-brief.md`
  summary: Slice-1 "equivalence: green" is stale relative to CFE v8.84.0, and guard clause (a) will pass a future compiled->parallel advancement -- the "re-port/re-validate before advancing" gate exists only as prose in next_action.
  evidence: Clause (a) gates only parallel/audited/cut-over and trusts the recorded enum (cfe_rebuild_guard_check.py:198-218; the existing tests pin both behaviors). Recording the staleness machine-readably (an equivalence value or an equivalence_as_of SHA that clause (a) can compare) belongs to the slice-1 re-validation work (Story 12.3's real-audit pass) -- this chore's intent authorized only the brief mirror + pointer flip, and rewriting the recorded green would falsify the corpus it was legitimately run against.
  location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:313
  origin: spec-deferred 236876ec2b22 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-1-3: The new "retro-mirror" amendment action is outside skf consumer enums, and skill-brief.v1.json does not constrain scope.amendments at all -- "schema valid" never inspected the new entries.

- source_spec: `planning-artifacts/specs/spec-12-1-landed-retros-are-mirrored-into-the-pilot-brief.md`
  summary: The new "retro-mirror" amendment action is outside skf consumer enums, and skill-brief.v1.json does not constrain scope.amendments at all -- "schema valid" never inspected the new entries.
  evidence: skf-provenance-gap-dispatch.py::_classify has a fixed action set (promoted/skipped/demoted-*); retro-mirror falls through to unresolved, which is fail-safe (surfaces for attention rather than hiding). The consequence path is speculative today -- both retro-mirrored paths are already in scope.include -- but recorded so the next skf schema/enum touch adds retro-mirror deliberately.
  origin: spec-deferred 7e94ac4eb19e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-2-1: DW-12-2-3: test_github_updater_gap_closed (test_slice1_equivalence.py) makes a live GitHub API call but is marked only @pytest.mark.slow, not @pytest.mark.network, so the new blocking test-ci gate's "-m 'not network'" selection does not actually exclude it.

- source_spec: `planning-artifacts/specs/spec-12-2-ci-enforcement-for-the-guard-and-the-equivalence-net.md`
  summary: DW-12-2-3: test_github_updater_gap_closed (test_slice1_equivalence.py) makes a live GitHub API call but is marked only @pytest.mark.slow, not @pytest.mark.network, so the new blocking test-ci gate's "-m 'not network'" selection does not actually exclude it.
  evidence: Verification-gap review confirmed the module-level skip guard does not trigger (.claude/skills/cfe-recipe-generation/active resolves; github_updater.py etc. exist), and the test's own docstring states it "does make a live network call on both sides now" since Story 6.3 ported github_version_checker.py, making _CHECKER_AVAILABLE True on both sides. A transient GitHub API failure or rate limit can red this blocking gate for reasons unrelated to any real CFE regression, undermining the offline-safety guarantee this story's own I/O matrix requires ("Avoids flaky CI from unreachable network calls"). Pre-existing since Story 6.3; only consequential now that this test runs inside a blocking gate for the first time. Cannot be fixed inside this story: the test file is under .claude/skills/conda-forge-expert/**, which the Never clause forbids mason from editing (mason-cfe-surface-check gate). Needs an owner who can add @pytest.mark.network to that test, or a suite-hygiene meta-check catching unmarked network calls.
  location: .claude/skills/conda-forge-expert/tests/integration/test_slice1_equivalence.py:149
  origin: spec-deferred a695de3ecb2d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: high
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-2-2: DW-12-2-4: cfe_rebuild_guard_check.py's clause-(b) unmirrored-retro commit scan walks every commit since a fixed baseline SHA with no rolling window or checkpoint, so its cost grows unbounded as repo history grows, and it now runs twice per PR (once inside the advisory repo-scope sweep, once more in the new dedicated blocking step).

- source_spec: `planning-artifacts/specs/spec-12-2-ci-enforcement-for-the-guard-and-the-equivalence-net.md`
  summary: DW-12-2-4: cfe_rebuild_guard_check.py's clause-(b) unmirrored-retro commit scan walks every commit since a fixed baseline SHA with no rolling window or checkpoint, so its cost grows unbounded as repo history grows, and it now runs twice per PR (once inside the advisory repo-scope sweep, once more in the new dedicated blocking step).
  evidence: Edge-case review measured roughly 1097 commits / 16s locally for the existing scan; blind review independently flagged the same unbounded-growth risk. Pre-existing design predating this story (it already ran inside the advisory sweep before Story 12.2); this story's dedicated blocking step doubles the per-PR cost inside the same job rather than introducing the unbounded-growth property itself. The re-run itself is the sanctioned branch-(a) approach recorded in this spec's Design Notes, not a defect to patch here.
  location: scripts/cfe_rebuild_guard_check.py
  origin: spec-deferred 2b0e73dcdfba — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-2-3: DW-12-2-5: commands-cheatsheet.md (CLAUDE.md's "canonical full recipe-lifecycle reference") documents test / test-all / test-coverage / test-recipes but was not updated to add the new test-ci task, so the cheatsheet goes stale the moment this story lands.

- source_spec: `planning-artifacts/specs/spec-12-2-ci-enforcement-for-the-guard-and-the-equivalence-net.md`
  summary: DW-12-2-5: commands-cheatsheet.md (CLAUDE.md's "canonical full recipe-lifecycle reference") documents test / test-all / test-coverage / test-recipes but was not updated to add the new test-ci task, so the cheatsheet goes stale the moment this story lands.
  evidence: Blind review confirmed the cheatsheet's Tests section lists only the pre-existing tasks. Real doc drift, but the file is under .claude/skills/conda-forge-expert/**, which the Never clause forbids mason from editing (mason-cfe-surface-check gate) -- needs an owner outside this story, e.g. the next conda-forge-expert skill retro.
  location: .claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md
  origin: spec-deferred cea54654215b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-3-1: skf-structural-diff.py has a name-collision/dedup bug: exports sharing the same name (e.g. four scripts each exporting `main`) collapse to one entry in the "added" list.

- source_spec: `planning-artifacts/specs/spec-12-3-the-real-audit-tool-backs-the-pilot-zero-drift-claim.md`
  summary: skf-structural-diff.py has a name-collision/dedup bug: exports sharing the same name (e.g. four scripts each exporting `main`) collapse to one entry in the "added" list.
  evidence: extraction-snapshot.json for this audit lists 73 exports (4 of them named `main`, one per script); structural-diff-result.json's "added" list contains only 70 entries with exactly one `main`, so 3 real export rows were silently dropped. Confirmed by direct inspection of both committed JSON artifacts. Excluded from this story's severity scoring already (the export-level diff was caveated as a baseline artifact), so it did not change the recorded verdict -- but the underlying tool bug is real and will undercount on every future audit of a multi-script skill with duplicate export names.
  location: _bmad/skf/shared/scripts/skf-structural-diff.py (dedup-by-name logic)
  origin: spec-deferred 7b7b754177e1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-3-2: cfe-recipe-generation's metadata.json records a dead doc source (a local filesystem path into a deleted ephemeral worktree), which crashes skf-detect-docs.py instead of failing gracefully.

- source_spec: `planning-artifacts/specs/spec-12-3-the-real-audit-tool-backs-the-pilot-zero-drift-claim.md`
  summary: cfe-recipe-generation's metadata.json records a dead doc source (a local filesystem path into a deleted ephemeral worktree), which crashes skf-detect-docs.py instead of failing gracefully.
  evidence: drift-report-20260828-073026.md's own Documentation Drift section: `doc_sources[0].url` is `.../.claude/worktrees/agent-a00a0f6206d94a499/README.md` -- a local path into a worktree that no longer exists, not a fetchable URL. `skf-detect-docs.py compare-hashes` raised `ValueError: unknown url type` on it this run; the doc-drift check was skipped per the workflow's own never-hard-halt rule. Pre-existing data-quality issue from Stories 6.1-6.3's original metadata.json authorship, surfaced incidentally by this story's audit run. Will recur on every future audit of this skill until the doc_sources entry is corrected to a repo-relative path (or removed).
  location: .claude/skills/cfe-recipe-generation/active/cfe-recipe-generation/metadata.json (doc_sources[0].url)
  origin: spec-deferred 59b5653417e5 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-4-1: spec-12-5's own Code Map suggests a top-level campaign-state.yaml field for the ownership decision, but Story 12.4 landed a nested field under campaign.re_scope_gate.pre_conditions instead, and the spec's own Block-If "flag for coordination" step wasn't exercised as a written artifact.

- source_spec: `planning-artifacts/specs/spec-12-4-the-re-scope-gate-is-machine-enforced.md`
  summary: spec-12-5's own Code Map suggests a top-level campaign-state.yaml field for the ownership decision, but Story 12.4 landed a nested field under campaign.re_scope_gate.pre_conditions instead, and the spec's own Block-If "flag for coordination" step wasn't exercised as a written artifact.
  evidence: Confirmed by reading spec-12-5-the-ownership-decision-is-recorded.md's Code Map directly. Mitigated in practice: campaign-state.yaml's own d_ownership_decision note already instructs Story 12.5 to "populate this entry -- do not invent a second key" -- but spec-12-5.md itself was not updated to match.
  location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md
  origin: spec-deferred bdd85f375a8c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-4-2: Clause (d) checks a self-reported campaign.re_scope_gate.pre_conditions.<key>.status field rather than independently verified state, unlike clauses (a)-(c) which each derive their verdict from something other than a hand-set flag.

- source_spec: `planning-artifacts/specs/spec-12-4-the-re-scope-gate-is-machine-enforced.md`
  summary: Clause (d) checks a self-reported campaign.re_scope_gate.pre_conditions.<key>.status field rather than independently verified state, unlike clauses (a)-(c) which each derive their verdict from something other than a hand-set flag.
  evidence: Confirmed by reading scan()'s clauses (a) (computed equivalence field), (b) (real git history via retro_commits_since), and (c) (campaign.callers entries) against clause (d)'s status-string membership check. The intent-contract's own Approach and AC text explicitly specify a recording-based check ("campaign-state.yaml does not record the four pre-conditions closed"), so this is a design observation the intent itself authorized, not a defect of this diff.
  location: scripts/cfe_rebuild_guard_check.py (clause (d), scan())
  origin: spec-deferred b5aebc5c8161 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-4-3: An explicit slice `id: null` (key present, value None) falls through `sl.get("id", "<unknown-slice>")`'s default, since the default only applies when the key is absent -- a finding would render the literal id value instead of the intended placeholder.

- source_spec: `planning-artifacts/specs/spec-12-4-the-re-scope-gate-is-machine-enforced.md`
  summary: An explicit slice `id: null` (key present, value None) falls through `sl.get("id", "<unknown-slice>")`'s default, since the default only applies when the key is absent -- a finding would render the literal id value instead of the intended placeholder.
  evidence: Confirmed via grep that this exact sl.get("id", "<unknown-slice>") pattern is shared verbatim by clauses (a) and (b), predating this story -- not introduced by clause (d)'s new code, which matches the file's existing style per this story's own Boundaries.
  location: scripts/cfe_rebuild_guard_check.py:322
  origin: spec-deferred 7ba4e7710f27 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-4-4: Pre-condition `status` matching (RE_SCOPE_GATE_SATISFIED_STATUSES) is case/whitespace-sensitive -- e.g. "Closed" would not satisfy the gate.

- source_spec: `planning-artifacts/specs/spec-12-4-the-re-scope-gate-is-machine-enforced.md`
  summary: Pre-condition `status` matching (RE_SCOPE_GATE_SATISFIED_STATUSES) is case/whitespace-sensitive -- e.g. "Closed" would not satisfy the gate.
  evidence: Confirmed via grep that clause (a)'s EQUIVALENCE_GATED_STATUSES membership check uses the same exact-string frozenset pattern with no case normalization anywhere in the file -- clause (d) matches established convention rather than introducing a new gap.
  location: scripts/cfe_rebuild_guard_check.py:178,325-327
  origin: spec-deferred fff94ae34801 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-5-1: The Operator ruling's own prose contains an ungrammatical phrase ("authored on and its stories carried by") mirrored verbatim into all three edited artifacts.

- source_spec: `planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md`
  summary: The Operator ruling's own prose contains an ungrammatical phrase ("authored on and its stories carried by") mirrored verbatim into all three edited artifacts.
  evidence: Blind-hunter review flagged the phrase as not parsing (likely meant "authored by" or "authored within"). It is part of the operator's own verbatim ruling text, not this story's implementation prose, so editing it without operator re-confirmation risks drift between the three mirrored copies.
  location: spec-12-5-the-ownership-decision-is-recorded.md:93 (mirrored into SPEC.md and campaign-state.yaml)
  origin: spec-deferred 2477539da6b6 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-5-2: The Operator ruling cites "CAP-19" as precedent without defining it anywhere in this SPEC's own Capabilities section or `sources:` frontmatter.

- source_spec: `planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md`
  summary: The Operator ruling cites "CAP-19" as precedent without defining it anywhere in this SPEC's own Capabilities section or `sources:` frontmatter.
  evidence: Blind-hunter review confirmed by grep that CAP-19 belongs to a different BMAD project (pyforge-steward) and is not cross-referenced from spec-conda-forge-expert-rebuild/SPEC.md, making the citation unresolvable from this file alone.
  location: spec-conda-forge-expert-rebuild/SPEC.md (Open Questions item 1, Resolved paragraph)
  origin: spec-deferred 174e934370f7 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-5-3: The Operator ruling's rationale is not cross-referenced against SPEC.md's own Non-goals §3, which frames the same legacy-vs-Kedro convergence question as "decided then, not now."

- source_spec: `planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md`
  summary: The Operator ruling's rationale is not cross-referenced against SPEC.md's own Non-goals §3, which frames the same legacy-vs-Kedro convergence question as "decided then, not now."
  evidence: Blind-hunter review noted the new Resolved note already leans on that same question (assigning Slice 3's brief to atlas specifically to force the convergence decision into atlas's hands) but neither section cross-references the other.
  location: spec-conda-forge-expert-rebuild/SPEC.md (Open Questions item 1 vs Non-goals §3)
  origin: spec-deferred e217e74adbf8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-5-4: The Code Map's cited precedent ("Story 5.4's own recheck-spec resolution-record pattern") doesn't structurally match the in-place list-annotation style this story actually used.

- source_spec: `planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md`
  summary: The Code Map's cited precedent ("Story 5.4's own recheck-spec resolution-record pattern") doesn't structurally match the in-place list-annotation style this story actually used.
  evidence: Blind-hunter review checked Story 5.4's actual precedent and found it to be a new "## Resolution record" section appended to the story's own spec file, not an in-place edit inserted into a numbered list inside a parent SPEC/PRD.
  location: spec-12-5-the-ownership-decision-is-recorded.md:80 (Code Map)
  origin: spec-deferred a73767276b6e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-5-5: This story's `context:` frontmatter doesn't list the sources the Operator ruling's rationale depends on (the CAP-19 material, the Phase-T/Epic-13 claim).

- source_spec: `planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md`
  summary: This story's `context:` frontmatter doesn't list the sources the Operator ruling's rationale depends on (the CAP-19 material, the Phase-T/Epic-13 claim).
  evidence: Blind-hunter review noted the rationale's "Precedent" argument is traceable only via prose assertion, not via any document this story declares as context.
  location: spec-12-5-the-ownership-decision-is-recorded.md:10-13 (frontmatter context:)
  origin: spec-deferred 712eabe8a82d — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-6-1: campaign-state.yaml's top-of-file "HOW TO RESUME" protocol reads only current_focus's own next_action, so a resuming session can miss a still-open next_action on a different slice.

- source_spec: `planning-artifacts/specs/spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md`
  summary: campaign-state.yaml's top-of-file "HOW TO RESUME" protocol reads only current_focus's own next_action, so a resuming session can miss a still-open next_action on a different slice.
  evidence: Established in Story 6.1, predates this story. campaign.current_focus was reassigned from slice-1 to slice-2 by this story; slice-1's own next_action (a targeted github_updater.py re-port) remains open and unresolved. This story added an adjacent comment flagging it, but the master resume-protocol one-liner near the top of the file still only names current_focus's slice.
  location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:11-12
  origin: spec-deferred 88dafeb4b73e — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-6-2: slice-map.md classifies test-skill.py as one of Slice 2's own canonical scripts, but it is a throwaway ad-hoc script unrelated to recipe lifecycle.

- source_spec: `planning-artifacts/specs/spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md`
  summary: slice-map.md classifies test-skill.py as one of Slice 2's own canonical scripts, but it is a throwaway ad-hoc script unrelated to recipe lifecycle.
  evidence: slice-map.md documents test-skill.py as a 10-line ad-hoc script hitting api.anaconda.org for a single package, with the real test-suite entrypoint living elsewhere. This story's brief inherited the entry verbatim from slice-map.md, which is this story's documented read-only Code Map source, not a file it may correct.
  location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  origin: spec-deferred 3cba2a495cd8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-6-3: Slice 2's brief_path lands inside this ephemeral dispatch worktree's gitignored implementation-artifacts/ with no promotion-to-durable-storage step, mirroring slice 1's own unresolved precedent.

- source_spec: `planning-artifacts/specs/spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md`
  summary: Slice 2's brief_path lands inside this ephemeral dispatch worktree's gitignored implementation-artifacts/ with no promotion-to-durable-storage step, mirroring slice 1's own unresolved precedent.
  evidence: Per this repo's own documented Tier-3-teardown incident (pyforge-warden lost 13 of 31 story specs to worktree teardown before a promotion convention existed for tracked story specs), a Tier-3 brief with no analogous promotion step risks the same fate. This story followed its own spec's explicit physical-path directive; the gap is systemic to the campaign's Tier-3 brief convention, not something this story introduced.
  location: _bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml
  origin: spec-deferred 54551e8df924 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-6-4: Slice 1's own brief_path still points at pyforge-atlas's implementation-artifacts tree rather than pyforge-mason's, a divergence from the parallel-agent physical-path rule that this story's spec explicitly flagged as precedent.

- source_spec: `planning-artifacts/specs/spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md`
  summary: Slice 1's own brief_path still points at pyforge-atlas's implementation-artifacts tree rather than pyforge-mason's, a divergence from the parallel-agent physical-path rule that this story's spec explicitly flagged as precedent.
  evidence: Documented in this story's own spec Boundaries section as slice 1's atypical landing location. Pre-existing state from Story 12.1, unchanged by this story, and out of this story's own boundaries (which govern only slice 2's brief_path).
  location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml (slice-1-recipe-generation entry)
  origin: spec-deferred 017538d2544a — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-7-1: Five of the 25 tracked scripts compute a repo-root/data-dir path via a hardcoded Path(__file__) parent-hop count that resolves one directory level short of the real repo root at this package's deeper nesting -- a real behavioral divergence risk for relative-path callers, confirmed live and documented, deliberately not patched.

- source_spec: `planning-artifacts/specs/spec-12-7-slice-2-compiled-and-equivalence-validated.md`
  summary: Five of the 25 tracked scripts compute a repo-root/data-dir path via a hardcoded Path(__file__) parent-hop count that resolves one directory level short of the real repo root at this package's deeper nesting -- a real behavioral divergence risk for relative-path callers, confirmed live and documented, deliberately not patched.
  evidence: Confirmed for recipe_editor.py: `pixi run -e local-recipes python .claude/skills/cfe-recipe-lifecycle/active/cfe-recipe-lifecycle/scripts/recipe_editor.py recipes/_probe/recipe.yaml '[...]'` (relative path, cwd=repo root) fails with "Recipe directory does not exist: .../.claude/skills/recipes/_probe" while the live original succeeds. Same root cause in _path_guard.py (REPO_ROOT = parents[4]), _paths.py's own get_repo_root() (same pattern -- ironic, since its own docstring documents this exact class of bug repo-wide), gen_yml_reference.py (visible in its own --help text, proven by test_slice2_equivalence.py::test_gen_yml_reference_help_diverges_by_known_path_depth_bug), and mapping_manager.py/vulnerability_scanner.py's un-.resolve()'d Path(__file__).parent.parent.parent.parent data-dir constant. Pre-existing, campaign-wide CFE debt (_paths.py's own Story-5.5 docstring already documents ~30-35 affected live-tree scripts), not introduced by this compile.
  location: .claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/scripts/{_path_guard.py,_paths.py,gen_yml_reference.py,mapping_manager.py,vulnerability_scanner.py}
  origin: spec-deferred ba53701027a8 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-7-2: 17 CLI wrapper files named in the brief's scope.include were deliberately not copied into the compiled package (each is a subprocess shim hardcoded to the live CFE tree), a scope interpretation this story made rather than one the brief/spec settled explicitly.

- source_spec: `planning-artifacts/specs/spec-12-7-slice-2-compiled-and-equivalence-validated.md`
  summary: 17 CLI wrapper files named in the brief's scope.include were deliberately not copied into the compiled package (each is a subprocess shim hardcoded to the live CFE tree), a scope interpretation this story made rather than one the brief/spec settled explicitly.
  evidence: slice-map.md and the brief list .claude/scripts/conda-forge-expert/*.py wrapper files under scope.include; Slice 1's own compiled package (cfe-recipe-generation) set the precedent of omitting analogous non-copyable scope.include entries (its guide/reference .md docs), which this story's implementation cites as justification. Documented fully in SKILL.md's Design Notes and evidence-report.md.
  location: .claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/SKILL.md (Design Notes)
  origin: spec-deferred 5536b0eb1d22 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-7-3: Two mason meta-tests (outside this story's own Code Map) were edited to exclude the CFE-rebuild campaign's own sanctioned equivalence-test file pattern from a generic "must not touch CFE" diff guard, to satisfy this story's own pyforge-mason-test verification bar.

- source_spec: `planning-artifacts/specs/spec-12-7-slice-2-compiled-and-equivalence-validated.md`
  summary: Two mason meta-tests (outside this story's own Code Map) were edited to exclude the CFE-rebuild campaign's own sanctioned equivalence-test file pattern from a generic "must not touch CFE" diff guard, to satisfy this story's own pyforge-mason-test verification bar.
  evidence: src/shared/packages/pyforge-mason/tests/meta/{test_persona_consults_cfe.py,test_portal_last_diagnose.py} both added a narrow regex exclusion (`.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py`). test_portal_last_diagnose.py's check post-dates Story 6.3's own landing of test_slice1_equivalence.py at this same path (confirmed via `git merge-base --is-ancestor`), so this is the first time the tension surfaced, not inherited red.
  location: src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py
  origin: spec-deferred 9e6df236f85b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-12-8-1: cfe_rebuild_guard_check.py's clause (d) enforces only campaign.re_scope_gate.pre_conditions, never re_scope_gate_2.pre_conditions, so a slice-3/4 brief_path write is not machine-blocked by this story's new gate.

- source_spec: `planning-artifacts/specs/spec-12-8-the-slice-2-re-scope-checkpoint.md`
  summary: cfe_rebuild_guard_check.py's clause (d) enforces only campaign.re_scope_gate.pre_conditions, never re_scope_gate_2.pre_conditions, so a slice-3/4 brief_path write is not machine-blocked by this story's new gate.
  evidence: Independently confirmed by 3 of 4 review-pass layers (Blind Hunter, Verification Gap Reviewer, Edge Case Hunter) against the diff since baseline_revision 7e84b9174d740a7a488ba3f5d50d9fea6d0784a4. clause (d) reads only campaign.get("re_scope_gate") and its four hardcoded RE_SCOPE_GATE_PRE_CONDITION_KEYS (a_ci_enforcement/b_skf_setup/ c_cross_slice_rederivation/d_ownership_decision) -- all four already status: closed today, so clause (d) is vacuously satisfied for any order>=2 slice's brief_path regardless of re_scope_gate_2's two new pre-conditions (slice1_equivalence_closure/slice2_equivalence_closure, both still open). tests/scripts/test_cfe_rebuild_guard_check.py has no test referencing re_scope_gate_2 either. This story's own Never-boundary explicitly forbids touching cfe_rebuild_guard_check.py's clause logic (matching Story 6.4's own GATHERED GAPS #5 precedent of naming an enforcement gap rather than closing it), so closing this is out of scope here -- deferred for a follow-up story to extend clause (d) (or add a clause (e)) to also read re_scope_gate_2.pre_conditions.
  location: scripts/cfe_rebuild_guard_check.py:304-341
  origin: spec-deferred 07db3769f77b — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-28 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

### DW-1-8-1: `render_text`'s shallow one-line-per-key rendering (Story 1.4) renders `mason doctor`'s default text-mode `engines` field as a raw Python tuple-of-dicts `repr()` on one unbroken line -- close to unreadable for a self-diagnosis tool whose main audience is a human troubleshooting their own setup.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `render_text`'s shallow one-line-per-key rendering (Story 1.4) renders `mason doctor`'s default text-mode `engines` field as a raw Python tuple-of-dicts `repr()` on one unbroken line -- close to unreadable for a self-diagnosis tool whose main audience is a human troubleshooting their own setup.
  evidence: Confirmed live — `mason doctor` (no `--format` flag) prints `engines: ({'name': 'pixi', 'available': True, ...}, {...}, ...)`. `render_text` is explicitly "NON-CONTRACT, free-format output" per its own module docstring and has never handled nested data specially; `doctor` is simply the first caller to hand it richly-nested data (every prior caller's `data` was flat). A real fix belongs to `render.py` generically (recursive/indented rendering for nested dicts/tuples), benefiting every future command with structured data, not a `doctor`-specific formatting special-case.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-8-2: `mason doctor` has no overall time budget — `engines.probe_known_engines()` probes four engines sequentially (up to 10s each) on top of `cfe.probe_import_floor`'s independent 15s subprocess timeout, so a single hung/slow engine binary or interpreter can make a "quick health check" command take up to roughly a minute with no progress output.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `mason doctor` has no overall time budget — `engines.probe_known_engines()` probes four engines sequentially (up to 10s each) on top of `cfe.probe_import_floor`'s independent 15s subprocess timeout, so a single hung/slow engine binary or interpreter can make a "quick health check" command take up to roughly a minute with no progress output.
  evidence: Confirmed by direct inspection — `probe_known_engines()` iterates `_KNOWN_ENGINES` with a plain generator expression (no concurrency), and `doctor.build_report` calls it after the (also serial) import-floor probe. No AC or boundary in this story's spec calls for parallelism or a shared timeout budget; a proper fix (e.g. `concurrent.futures`-based fan-out with one overall deadline) is a deliberate design change worth its own story, not a one-off patch here.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-8-3: `resolve_cfe_root`'s explicit-flag and environment-variable steps (Story 1.5) trust the given path without checking the CFE marker directory exists there — an explicit `--cfe-root`/`MASON_CFE_ROOT` pointing at a bogus path is reported by `mason doctor` as "resolved," with `"recipe"` NOT listed as unavailable, even though CFE isn't actually there.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `resolve_cfe_root`'s explicit-flag and environment-variable steps (Story 1.5) trust the given path without checking the CFE marker directory exists there — an explicit `--cfe-root`/`MASON_CFE_ROOT` pointing at a bogus path is reported by `mason doctor` as "resolved," with `"recipe"` NOT listed as unavailable, even though CFE isn't actually there.
  evidence: Confirmed intentional and pre-existing — `resolve.py`'s own module docstring states "Steps 1 and 2 match on the presence of a non-whitespace value alone... and are NOT validated against the marker directory; only step 3 (the walk) checks for it." `doctor.py` (this story) faithfully reports whatever `resolve_cfe_root` returns, so the gap is inherited, not introduced. It does work against the epic's own framing of `doctor` telling "the truth about what it cannot do," so it's worth deliberate reconsideration in `resolve.py` itself (Story 1.5's territory) rather than a doctor-local workaround.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-9-1: `pyforge-mason/spec-pyforge-mason`'s own `.memlog.md` has moved since the surface-drift baseline was last stamped, but the move doesn't name 23 of the governed files it actually covers (Story 1.9's own new fixture/test/pixi files among them) — `spec_surface_check.py` reports these as `[drift-presumed]`, informational and non-gating by the detector's own design, not a failure of this story.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-9-fake-cfe-root-fixture-and-test-harness.md`
  summary: `pyforge-mason/spec-pyforge-mason`'s own `.memlog.md` has moved since the surface-drift baseline was last stamped, but the move doesn't name 23 of the governed files it actually covers (Story 1.9's own new fixture/test/pixi files among them) — `spec_surface_check.py` reports these as `[drift-presumed]`, informational and non-gating by the detector's own design, not a failure of this story.
  evidence: Confirmed live via `python3 scripts/spec_surface_check.py` after this story's verification repair: `DRIFT-PRESUMED (23 across 1 spec(s)) — pyforge-mason/spec-pyforge-mason`, e.g. `src/shared/packages/pyforge-mason/pyproject.toml` and `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py`. Reconciling it (naming all 23 paths in the mason spec's own memlog) is a mason-spec-authoring action, not a code fix, and belongs to whoever next moves that memlog rather than this verification-repair pass.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-10-3: `pyforge-mason/planning-artifacts/test-architecture.md`'s Story 1.10 row requires "a streaming child-process test asserts stderr passes through live while `--format json` still emits exactly one stdout document" — no such CLI-level integration test exists, and this story's own frozen intent-contract Never boundary ("nothing calls a CFE script yet; this story only adds the flag/env/resolver... this story ships only the low-level STREAM primitive") makes it impossible to write today: no CLI command wires `run_streamed` into dispatch yet.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: `pyforge-mason/planning-artifacts/test-architecture.md`'s Story 1.10 row requires "a streaming child-process test asserts stderr passes through live while `--format json` still emits exactly one stdout document" — no such CLI-level integration test exists, and this story's own frozen intent-contract Never boundary ("nothing calls a CFE script yet; this story only adds the flag/env/resolver... this story ships only the low-level STREAM primitive") makes it impossible to write today: no CLI command wires `run_streamed` into dispatch yet.
  evidence: Confirmed by reading `test-architecture.md` line 122 directly and cross-checking against the story spec's Code Map/Never boundary — the two planning artifacts are in tension. AD-25's actual guarantee ("stdout's single-JSON-document guarantee holds unbroken during a streaming operation") is already proven at the correct layer today: `run_streamed` never writes to Mason's own `sys.stdout` under any `--format`, verified by the existing `test_run_streamed_returned_stdout_is_isolated_from_masons_own_stdout`. A literal `--format json` CLI-integration test becomes possible, and should be added, once Story 2.1 wires `run_streamed` into an actual noun's dispatch — reconcile the two artifacts at that point rather than in this repair pass, which must not touch the frozen intent-contract.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-10-4: `run_streamed` accumulates the child's entire stdout in memory (`proc.stdout.read()` into one Python string) with no cap, in a primitive whose own module docstring names `recipe build`/`package build` — multi-minute conda builds that can emit hundreds of MB — as its intended callers.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: `run_streamed` accumulates the child's entire stdout in memory (`proc.stdout.read()` into one Python string) with no cap, in a primitive whose own module docstring names `recipe build`/`package build` — multi-minute conda builds that can emit hundreds of MB — as its intended callers.
  evidence: Confirmed by direct inspection of `cfe.py`'s `_capture_stdout`. Not a defect in this story's delivered scope: "captures its stdout in full" is the function's stated contract, and AD-25's CAPTURE-side counterpart (`probe_import_floor`) reads a handful of marker lines, so nothing today produces a large stdout. It becomes real once Story 2.1's adapter points this at an actual CFE build script. A fix (bounded ring-buffer capture, spill-to-temp-file, or a `max_stdout_bytes` parameter that truncates with an explicit marker) changes the return contract and belongs with Story 2.1's `CfeResult` design, which this story's Never boundary explicitly excludes.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-10-5: When `run_streamed` times out, every byte of stdout captured before the deadline is discarded — the `subprocess.TimeoutExpired` propagates with `.stdout` unset, and the local `captured_stdout` list is dropped on the way out.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: When `run_streamed` times out, every byte of stdout captured before the deadline is discarded — the `subprocess.TimeoutExpired` propagates with `.stdout` unset, and the local `captured_stdout` list is dropped on the way out.
  evidence: Confirmed by direct inspection and reproduced: a child that flushes a marker to stdout then sleeps past the timeout raises `TimeoutExpired` whose `.stdout` is `None`. This diverges from `subprocess.run(timeout=...)`, which attaches partial output to the exception, and from this same file's `probe_import_floor`, whose whole design deliberately credits partial output from a child that died early. Low consequence today: STREAM mode's diagnostic channel is stderr, which was already forwarded live and is visible to the user, and a timed-out operation has no complete JSON document on stdout anyway. Populating `exc.stdout` is adjacent to the typed-timeout-error contract this story's Never boundary forbids building ("Build Story 2.1's `CfeResult` ... or a typed timeout error"), so it belongs with Story 2.1's failure contract.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-10-6: `run_streamed` lets a `Popen` spawn failure (`OSError`/`FileNotFoundError` — `argv[0]` missing, not executable, or an `env=` mapping with no usable `PATH`) escape raw, so it would reach a user as a Python traceback via `main()`'s bare-`Exception` boundary rather than as an AD-7 anticipated failure with an identifier and no traceback.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: `run_streamed` lets a `Popen` spawn failure (`OSError`/`FileNotFoundError` — `argv[0]` missing, not executable, or an `env=` mapping with no usable `PATH`) escape raw, so it would reach a user as a Python traceback via `main()`'s bare-`Exception` boundary rather than as an AD-7 anticipated failure with an identifier and no traceback.
  evidence: Confirmed by direct inspection — the `Popen(...)` call sits outside any `except OSError` guard, and `cli.py:main`'s final `except Exception` clause prints `traceback.print_exc()` and returns `EXIT_FAILED`. Not reachable today: `run_streamed` has no production caller (this story ships the primitive only). Sibling precedent already exists for the right shape — `probe_import_floor` catches `OSError` and folds it into a domain outcome rather than propagating — but choosing the domain outcome here (a typed CFE error vs. a `CfeResult` failure value) is exactly the Story 2.1 error-contract decision this story's Never boundary excludes.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-1-10-7: In the grandchild-holds-the-pipes degraded path, `run_streamed` now deliberately leaves that pipe open and its daemon reader thread blocked and running past the function's own return — two leaked file descriptors and a live thread per occurrence — because closing a pipe whose reader is still blocked deadlocks the caller. Both this and the already-logged "no true partial capture on that path" limitation dissolve together under a chunked/non-blocking reader redesign, which is the real fix neither can have separately.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: In the grandchild-holds-the-pipes degraded path, `run_streamed` now deliberately leaves that pipe open and its daemon reader thread blocked and running past the function's own return — two leaked file descriptors and a live thread per occurrence — because closing a pipe whose reader is still blocked deadlocks the caller. Both this and the already-logged "no true partial capture on that path" limitation dissolve together under a chunked/non-blocking reader redesign, which is the real fix neither can have separately.
  evidence: Confirmed by direct inspection and by measurement during the 2026-08-10 fourth review pass. The unconditional close this replaces was reproduced hanging at 45.02s against a documented 10s bound (and swallowing `TimeoutExpired` outright on the timeout path), so leaking the descriptor is strictly the better of the two available behaviors — but it is a leak, and the suite only stays clean under `-W error::ResourceWarning` because the new regression test closes the pipes itself once it has killed the grandchild. A proper fix reads each pipe in bounded non-blocking chunks with a shared deadline instead of one blocking `read()`/line-iterator per stream, so a reader can be told to stop and its pipe closed safely; that also yields the genuine partial capture `_JOIN_GRACE_SECONDS`'s docstring currently has to disclaim, and the bounded-capture behavior the unbounded-stdout entry above asks for. It is a redesign of the primitive's I/O core, not a patch, and it wants a real caller to size it against — Story 2.1's adapter, whose `CfeResult`/error contract this story's Never boundary excludes.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-1: Both `test_no_recipe_knowledge.py` and `test_adapter_sole_caller.py` scan literal AST nodes (string/bytes constants, identifier positions, direct call shapes) only — a denied term or CFE path assembled via string concatenation (`"a" + "b"`), an f-string, a `bytes`-then-decode round-trip beyond the simple case already handled, indirect rebinding (`spawn = subprocess.run; spawn(...)`), or a dynamically-resolved call target (`getattr(subprocess, "run")(...)`) evades every detector in both files.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: Both `test_no_recipe_knowledge.py` and `test_adapter_sole_caller.py` scan literal AST nodes (string/bytes constants, identifier positions, direct call shapes) only — a denied term or CFE path assembled via string concatenation (`"a" + "b"`), an f-string, a `bytes`-then-decode round-trip beyond the simple case already handled, indirect rebinding (`spawn = subprocess.run; spawn(...)`), or a dynamically-resolved call target (`getattr(subprocess, "run")(...)`) evades every detector in both files.
  evidence: Confirmed by direct inspection of both scanners' matching logic (string-constant/identifier equality and a fixed call-name allowlist, no dataflow tracing) and by manually tracing each evasion shape through the code. Zero current occurrences in the real tree (all 458 tests green). Properly closing this requires dataflow/taint analysis or an import-alias-resolution pass well beyond AST-node-type matching — a redesign of the detection methodology, not a trivial patch. Notably, Story 2.1's own `test_dependency_direction.py` AD-4 guard explicitly punted "indirect rebinding... reflective lookups" to "Story 2.2's dedicated, more thorough seam-guard methodology" — this story closes several concrete gaps (identifier positions, bytes literals, qualified-path allowlisting, expanded subprocess-call coverage) but does not achieve full obfuscation-resistance; a future story should decide whether that bar is worth pursuing.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-2: `test_no_recipe_knowledge.py`'s check-code-prefix pattern (`\b(?:ABT|DEP|FMT|LIC|MAINT|PIN|SCHEMA|SCRIPT|SEC|SEL|STD|TEST)-\d{3}\b`) and gotcha-identifier pattern (`\bG[0-9]{1,3}\b`) are, by their own defining shape, indistinguishable from unrelated conventions Mason doesn't currently use — a generic issue-tracker ID (`TEST-042`, `SEC-001`, `DEP-100` are common Jira/GitHub shapes) or an unrelated domain term (`G1` the JVM garbage collector, `G7`/`G20` economic groupings) would trip the guard for reasons unrelated to CFE recipe knowledge.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: `test_no_recipe_knowledge.py`'s check-code-prefix pattern (`\b(?:ABT|DEP|FMT|LIC|MAINT|PIN|SCHEMA|SCRIPT|SEC|SEL|STD|TEST)-\d{3}\b`) and gotcha-identifier pattern (`\bG[0-9]{1,3}\b`) are, by their own defining shape, indistinguishable from unrelated conventions Mason doesn't currently use — a generic issue-tracker ID (`TEST-042`, `SEC-001`, `DEP-100` are common Jira/GitHub shapes) or an unrelated domain term (`G1` the JVM garbage collector, `G7`/`G20` economic groupings) would trip the guard for reasons unrelated to CFE recipe knowledge.
  evidence: Confirmed by direct pattern analysis; zero current false positives (all 458 tests green, and neither shape appears anywhere in the real tree today). This is an accepted, essentially irreducible trade-off of using short-prefix/short-identifier pattern matching at all — real CFE check codes and gotcha IDs are genuinely shaped this way (per `SKILL.md`'s own catalog), so narrowing the pattern further would risk missing real violations. No better mechanical fix identified; would need human judgment if it ever fires on a real, unrelated future usage.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-3: `test_no_recipe_knowledge.py`'s pin-shape pattern (`(?:==|!=|<=|>=|~=|<|>)\s*\d`) matches a single comparison-operator-before-a-digit occurrence anywhere in a string constant, with no requirement that it appear as part of a real conda-forge pin expression (e.g. a paired lower/upper bound like `">=1.0,<2.0"`) — an unrelated future string like `"value must be <100"` or a URL fragment would trip it.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: `test_no_recipe_knowledge.py`'s pin-shape pattern (`(?:==|!=|<=|>=|~=|<|>)\s*\d`) matches a single comparison-operator-before-a-digit occurrence anywhere in a string constant, with no requirement that it appear as part of a real conda-forge pin expression (e.g. a paired lower/upper bound like `">=1.0,<2.0"`) — an unrelated future string like `"value must be <100"` or a URL fragment would trip it.
  evidence: Confirmed by direct pattern analysis; zero current false positives (all 458 tests green). A precise fix (requiring two operator+digit occurrences joined by a comma, mirroring the real `">=X,<Y"` shape from `reference/pinning-reference.md`) is a bigger, more brittle redesign that risks missing single-bound pins (`"==1.2.3"`, a real, valid conda-forge exact-pin shape with only one operator) — the current single-occurrence pattern trades false-positive tolerance for not missing that case, a deliberate choice worth revisiting only if a real false positive is observed.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-4: `test_adapter_sole_caller.py`'s subprocess-spawn detector (`_is_subprocess_spawn_call`) matches on bare attribute/function name only (`run`, `Popen`, `system`, etc.), with no resolution of the receiver's import origin — an unrelated method or function sharing one of these names (e.g. a hypothetical future `SomeClass.run(...)` unconnected to `subprocess`) whose arguments happen to contain a CFE-shaped string would be flagged as a false "spawned a process against CFE" violation, and conversely a genuine spawn via an unrecognized indirect form (`getattr(subprocess, "run")(...)`) evades detection entirely.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: `test_adapter_sole_caller.py`'s subprocess-spawn detector (`_is_subprocess_spawn_call`) matches on bare attribute/function name only (`run`, `Popen`, `system`, etc.), with no resolution of the receiver's import origin — an unrelated method or function sharing one of these names (e.g. a hypothetical future `SomeClass.run(...)` unconnected to `subprocess`) whose arguments happen to contain a CFE-shaped string would be flagged as a false "spawned a process against CFE" violation, and conversely a genuine spawn via an unrecognized indirect form (`getattr(subprocess, "run")(...)`) evades detection entirely.
  evidence: Confirmed by direct inspection of `_is_subprocess_spawn_call`'s bare `ast.Attribute`/`ast.Name` matching, with no cross-reference to import statements (unlike `test_dependency_direction.py`'s `_collect_import_module_aliases`, which does resolve aliasing for its own, narrower `importlib` check). Zero current false positives or false negatives (all 458 tests green; the real tree has no such collision). A precise fix would trace `import subprocess`/`import os`/`import asyncio` aliasing through to each call site, mirroring `test_dependency_direction.py`'s existing alias-resolution pattern — a real, bounded improvement, but a larger change than this pass's other patches and not blocking today.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-5: Every meta-guard that walks the package tree globs `*.py` only, so a `.pyi` stub — or any package subdirectory reached through a directory symlink — is outside the coverage of all six guards, including the two AD-1/AD-3 guards this story adds, whose invariants are stated in absolute terms ("no module under `pyforge/mason/` may…", "only `cfe.py` may…").

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: Every meta-guard that walks the package tree globs `*.py` only, so a `.pyi` stub — or any package subdirectory reached through a directory symlink — is outside the coverage of all six guards, including the two AD-1/AD-3 guards this story adds, whose invariants are stated in absolute terms ("no module under `pyforge/mason/` may…", "only `cfe.py` may…").
  evidence: Confirmed by direct inspection of the `rglob("*.py")` call in `test_dependency_direction.py:55/257`, `test_render_ownership.py:85`, `test_no_config_file.py:84`, `test_exit_code_ownership.py:88` and both new files, and reproduced by the review: a synthetic `doctor.pyi` declaring `def build(*, run_exports: list = ...)` alongside `P: str = ".claude/scripts/conda-forge-expert"` produces zero violations from either new scanner, and modules placed under a symlinked subdirectory are never visited (`Path.rglob` does not follow directory symlinks before Python 3.13's `recurse_symlinks=`). Pre-existing rather than introduced here — the four sibling guards predate this story and share the boundary exactly — and inert today: `src/pyforge/mason/` contains no `.pyi` file and no symlinked subdirectory. Worth closing suite-wide in one deliberate pass (extend the glob, or assert the absence of both shapes) rather than diverging one story's two files from the other four.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-6: The four sibling meta-guards read source with `encoding="utf-8"`, so a BOM-prefixed module — perfectly runnable Python — reaches `ast.parse` with a leading `﻿` and is reported as "invalid Python syntax", failing the guard against a valid file with a message that misdescribes the cause.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: The four sibling meta-guards read source with `encoding="utf-8"`, so a BOM-prefixed module — perfectly runnable Python — reaches `ast.parse` with a leading `﻿` and is reported as "invalid Python syntax", failing the guard against a valid file with a message that misdescribes the cause.
  evidence: Reproduced during review against the two new files before they were switched to `utf-8-sig`; the same `path.read_text(encoding="utf-8")` call remains at `test_capability_tiers.py:120`, `test_render_ownership.py:89`, `test_exit_code_ownership.py:92` and `:137`, `test_dependency_direction.py:59`, `:259` and `:452`, and `test_namespace_is_implicit.py:43`. Pre-existing and not introduced here; the correct spelling already exists in-suite at `test_no_config_file.py:92` (`utf-8-sig`), which this story's two files now match, so the fix is a one-word change per call site rather than a design question. Inert today — no file in the tree carries a BOM — and left out of this story's diff because its Code Map covers only the two new files.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-7: `test_adapter_sole_caller.py`'s `_CFE_PATH_SUBSTRING` match has no trailing boundary, so any sibling path merely sharing the prefix — `.claude/scripts/conda-forge-expert-notes.md`, a future `…-shim/` directory — is reported as a CFE-wrapper reference in the one category whose only escape hatch is a deliberately pinned two-entry allowlist.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: `test_adapter_sole_caller.py`'s `_CFE_PATH_SUBSTRING` match has no trailing boundary, so any sibling path merely sharing the prefix — `.claude/scripts/conda-forge-expert-notes.md`, a future `…-shim/` directory — is reported as a CFE-wrapper reference in the one category whose only escape hatch is a deliberately pinned two-entry allowlist.
  evidence: Reproduced during review: `_names_a_cfe_path(".claude/scripts/conda-forge-expert-notes.md")` returns `True`. Zero current occurrences (all 537 tests green; no such sibling path exists). Left unfixed deliberately this pass: a trailing-boundary requirement (end-of-string, `/`, or a quote) has to stay correct across the literal, backslash-spelled, separator-collapsed and segment-assembled forms the same predicate now serves, so it is a real change to a hot path in exchange for suppressing an over-detection that is arguably correct anyway — anything under `.claude/scripts/conda-forge-expert*` is CFE-adjacent. Worth doing only alongside a deliberate decision about how narrow AD-3's path category should be.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-8: All six meta-guards decode source themselves (`read_text(encoding="utf-8"/"utf-8-sig")`) before handing text to `ast.parse`, so a module declaring a non-UTF-8 source encoding via a PEP 263 coding cookie (`# -*- coding: latin-1 -*-`) is reported as "not valid UTF-8" or "invalid Python syntax" against a file CPython imports without complaint.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: All six meta-guards decode source themselves (`read_text(encoding="utf-8"/"utf-8-sig")`) before handing text to `ast.parse`, so a module declaring a non-UTF-8 source encoding via a PEP 263 coding cookie (`# -*- coding: latin-1 -*-`) is reported as "not valid UTF-8" or "invalid Python syntax" against a file CPython imports without complaint.
  evidence: Confirmed by direct inspection of `_read_source` in both new files and the equivalent reads in the four siblings; CPython honours the cookie only when `ast.parse` is handed **bytes**, which none of them do. Inert today — every file in `src/pyforge/mason/` is UTF-8 and the repo has no cookie anywhere — and distinct from the BOM defect already logged above (that one is a per-call-site one-word fix; this one changes the read path, and with it the two clean-failure contracts every guard asserts on unreadable/undecodable input). Belongs with the suite-wide encoding pass that ledger entry already anticipates, not to one story's two files.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-9: AD-3's category-(a) carve-out is file-LEVEL by spec, so an allowlisted file (`resolve.py`/`errors.py`) may build any CFE path — not just the one constant it was exempted for — and hand it to a caller, and the only backstop left inside those two files is category (c)'s finite name list; narrowing the carve-out to the two named constants is a design decision about AD-3's granularity, not a patch.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: AD-3's category-(a) carve-out is file-LEVEL by spec, so an allowlisted file (`resolve.py`/`errors.py`) may build any CFE path — not just the one constant it was exempted for — and hand it to a caller, and the only backstop left inside those two files is category (c)'s finite name list; narrowing the carve-out to the two named constants is a design decision about AD-3's granularity, not a patch.
  evidence: Reproduced after this pass's fixes: `resolve.py` containing `def go(root, name, launch): return launch(root / '.claude' / 'scripts' / 'conda-forge-expert' / name)` scans clean, as does the two-module split where `resolve.py` returns the assembled path and a separate `engines.py` runs `subprocess.run(['python', str(cfe_script(r, n))])`. The identical shape in a non-allowlisted file is flagged (`cfe-path`), so the exemption — not the detector — is what admits it. Category (b) cannot backstop either case because the script name is a variable, and this pass already widened category (c) as far as a name list can go (`pty`/`runpy`/`multiprocessing` added). Closing it properly means either scoping the exemption to the specific constant (`_CFE_MARKER`, `CfeUnresolvedError._MESSAGE`) rather than the whole file, or capping each carve-out file at one CFE-path expression — both deviate from the spec's explicit "two-entry allowlist is file-level" wording and both risk a false red on `errors.py`'s prose, which is a user-facing sentence that legitimately embeds the path and is reworded freely. Zero current occurrences; all 559 tests green.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-2-10: The three anti-mutation floor tables (`_REQUIRED_SPAWN_CALL_NAMES`, `_REQUIRED_V1_FIELD_NAMES`, `_REQUIRED_CHECK_CODE_PREFIXES`) are hand-mirrored verbatim copies of the live tables asserted in one direction only (`required ⊆ live`), so every entry ADDED to a live table silently arrives with no floor entry and therefore no parametrized detection fixture — reintroducing, on each widening, the exact "membership is not detection" gap the floors were added to close.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-the-seam-guard.md`
  summary: The three anti-mutation floor tables (`_REQUIRED_SPAWN_CALL_NAMES`, `_REQUIRED_V1_FIELD_NAMES`, `_REQUIRED_CHECK_CODE_PREFIXES`) are hand-mirrored verbatim copies of the live tables asserted in one direction only (`required ⊆ live`), so every entry ADDED to a live table silently arrives with no floor entry and therefore no parametrized detection fixture — reintroducing, on each widening, the exact "membership is not detection" gap the floors were added to close.
  evidence: Confirmed by direct inspection of the three floor tests, which all assert `required - live == set()` and never the reverse; the deliberate duplication is itself documented (a derived floor would delete itself alongside a dropped entry, which is why it must stay independent). Reproduced in effect by this pass: four names were added to `_SUBPROCESS_CALL_NAMES` and would have had zero coverage had the floor not been edited by hand in the same diff — nothing mechanical would have caught the omission. Zero current drift (all three pairs are in sync; 559 tests green). A `live - required` warning, or a single source table plus a checked-in count, would keep the anti-mutation property without relying on a maintainer editing two literals in lockstep; left alone here because it changes the shape of a guard mechanism the spec pins by name and touches both new files plus their floor tests.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-3-3: All three AST-scanning meta-test files (`test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py`, and this story's new `test_credential_isolation.py`) share `_parse_source` helpers that catch only `SyntaxError` from `ast.parse`, not the `ValueError` it raises for a source file containing a null byte — such a file would escape as an unhandled traceback instead of each guard's own documented clean-`AssertionError` contract.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-3-credential-isolation.md`
  summary: All three AST-scanning meta-test files (`test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py`, and this story's new `test_credential_isolation.py`) share `_parse_source` helpers that catch only `SyntaxError` from `ast.parse`, not the `ValueError` it raises for a source file containing a null byte — such a file would escape as an unhandled traceback instead of each guard's own documented clean-`AssertionError` contract.
  evidence: Confirmed by direct inspection of all three files' `_parse_source` functions (identical `except SyntaxError` clause, no `except ValueError`). Pre-existing in the two sibling files this story's guard deliberately mirrors — not introduced here, since the new file faithfully replicated the established pattern rather than deviating from it. A proper fix belongs to all three files together in one pass (consistent with how `test_exit_code_ownership.py`'s identical-shaped `path.resolve()` gap is already logged above as a multi-file fix), not a unilateral deviation in only the newest file.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open

### DW-2-3-4: The "attribute docstring" exemption shared by `test_no_recipe_knowledge.py` and this story's `test_credential_isolation.py` recognizes a bare string statement only when it follows an `ast.Assign`/`ast.AnnAssign` at module or class level — so the same PEP 257-adjacent prose following an `ast.AugAssign`, or appearing inside a function body, is scanned as a live string constant and can false-positive the guard on its own explanatory text.

- source_spec: `_bmad-output/implementation-artifacts/spec-2-3-credential-isolation.md`
  summary: The "attribute docstring" exemption shared by `test_no_recipe_knowledge.py` and this story's `test_credential_isolation.py` recognizes a bare string statement only when it follows an `ast.Assign`/`ast.AnnAssign` at module or class level — so the same PEP 257-adjacent prose following an `ast.AugAssign`, or appearing inside a function body, is scanned as a live string constant and can false-positive the guard on its own explanatory text.
  evidence: Reproduced against the new guard: `X += 1` followed by a bare string naming `JFROG_API_KEY`, and an assignment-plus-trailing-string pair inside a function body, are both flagged as violations, while the identical prose after a module-level `X = 1` is correctly exempt. This is an inherited limitation, not a mirroring-claim violation — `test_no_recipe_knowledge.py:425-483` has the identical shape, and this story's file faithfully replicated it rather than deviating. It matters more here than in the sibling because AD-14's whole subject matter invites production docstrings that name `JFROG_*` variables in prose, and the cheapest repair under a red guard is to weaken the guard. Belongs to both files in one pass, alongside the `_parse_source`/null-byte entry logged above, rather than a unilateral deviation in only the newest file. Zero current occurrences; 664 tests green.
  promoted: 2026-08-28 — promoted from Tier-3 implementation-artifacts/deferred-work.md (legacy legacy-flat entry, no prior id)
  status: open
