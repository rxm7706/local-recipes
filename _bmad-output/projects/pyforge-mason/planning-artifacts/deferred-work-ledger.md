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

### DW-1-3-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-error-taxonomy-and-exit-code-contract.md`
  summary: `tests/meta/test_exit_code_ownership.py`'s `_find_rogue_exit_code_owners` calls `path.resolve()` (to compare against the owner path) before entering the `try`/`except OSError` block that protects `read_text`, so a path that raises `OSError` on `resolve()` itself (e.g. a symlink loop, `ELOOP`) would escape as a raw traceback instead of the file's own documented clean-`AssertionError` contract.
  evidence: Confirmed by direct inspection of the new file's `_find_rogue_exit_code_owners`, and this is not a new defect introduced by Story 1.3 — the file's own docstring states it "mirrors `test_dependency_direction.py`'s approach," and that pre-existing file's `_find_subprocess_importers` has the identical `path.resolve() in allowed` check ahead of its own `try` block (confirmed by reading that file). Fixing only the new file would be inconsistent with the sibling it deliberately mirrors; a proper fix belongs to both meta-test files together in one pass, not a unilateral deviation introduced here.
  status: open

### DW-1-4-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`
  summary: `render.py`'s `write()` calls `stream.write(...)`/`stream.flush()` with no `BrokenPipeError`/`OSError` guard, so `mason doctor | head -1` (or any consumer that closes the pipe early) would let the write itself escape uncaught into `main()`'s generic `except Exception` handler — a raw traceback and `EXIT_INTERNAL` instead of a clean, expected broken-pipe exit.
  evidence: Confirmed by direct inspection — `write()`'s two-line body has no try/except around the stream I/O. This joins the exact same family already logged above from Story 1.3 (`cli.py`'s stderr writes are unguarded the same way) rather than duplicating it: that entry already recommends "a single pass across all of `cli.py`'s stderr call sites together, most naturally once Story 1.4's `render.py` becomes the sole output writer" — but Story 1.3's `MasonError`-handler call site doesn't exist in this branch yet (developing in an unmerged sibling worktree), so a unified pass covering every stdout+stderr write call site together isn't possible until that merges. Fixing only `render.py`'s new call site now would repeat the same piecemeal-fix problem the existing entry warns against.
  status: open

### DW-1-4-2

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`
  summary: `render_json`/`render_text` have no defensive handling for a `data`/`errors` value `json.dumps` can't serialize (e.g. a `Path` or `datetime`) — `render_json` would raise an unhandled `TypeError` instead of a clean, actionable failure.
  evidence: Confirmed by direct inspection — no `default=` fallback or type-normalization exists before the `json.dumps` call. Not triggered by any current caller (`doctor`'s stub only ever passes a plain string `message`), so it is not a defect in this story's own delivered scope; it will matter once `recipe.py`/`package.py`/`environment.py` land in later epics and start returning richer data shapes (paths, versions, timestamps) through `render.write`.
  status: open

### DW-1-10-1

- source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.md`
  summary: follow-up review still recommended for 1-10 after the damping cap was spent — an independent pass is owed on the configuration surface, logging, and child-output streaming.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260809-231234-a3cb`. 1-10 also ran to both ceilings — dev attempt 2/2 and review cycle 3/3 — and cleared on its LAST cycle rather than escalating, which is exactly the profile where an independent pass is worth spending.
  promoted: 2026-08-10 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there) under THIS ledger's own `DW-<story>-<n>` convention (`DW-1-3-1`, `DW-1-4-1`, `DW-1-4-2`), which differs from doctor's and atlas's `DW-FU-<story>`; the station's own precedent wins. A generic `DW-1` would collide with the next damped story, and Tier-3 is gitignored so the entry would not survive a clone. Marshal Story 4.13 — landed earlier today in PR #381 — exists to make this promotion an obligation of the story rather than archaeology someone performs later.
  status: open

### DW-2: Follow-up review still recommended for 2-2-the-seam-guard after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-2-2-the-seam-guard.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-193147-b96d; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, mason 2-2 / marshal 7-4)


### DW-2-3-1

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-3-credential-isolation.md`
  summary: follow-up review still recommended for 2-3 after the damping cap was spent — an independent pass is owed on the AD-14 credential-isolation guard.
  evidence: the follow-up-review damping cap (`limits.max_followup_reviews = 2`) was spent with the story finalized (status `done`, verify green) while the review pass still recommended an independent follow-up. Committed by bmad-loop run `20260810-193147-b96d`. The story ran to 3 review cycles, each closing real bypasses (env aliasing, indirect mutation methods, non-assignment binding targets, explicit-environment spawn functions), which is the profile where an independent pass is worth spending.
  promoted: 2026-08-11 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-3` there) under this ledger's own `DW-<epic>-<story>-<n>` convention, renamed to avoid colliding with the next damped story (bmad-loop always emits a generic id).
  status: open

### DW-4-4-5

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `test_every_sanctioned_yaml_exception_is_live_and_import_form_scoped` (`tests/meta/test_no_config_file.py:194-228`) does not enforce the invariant its own docstring claims. It asserts only on `ast.ImportFrom`, but the sanctioned `import yaml` form exposes `yaml.unsafe_load` identically via attribute access, and `_SANCTIONED_YAML_EXCEPTIONS` keys on `(path, banned_module)`, blanket-exempting the whole file.
  evidence: Review-verified live — substituting `yaml.unsafe_load` for `yaml.safe_load` in `_read_content_hash` leaves the meta suite green. Fix: add an `ast.Attribute` walk asserting `yaml.<attr>` is only ever `safe_load`.
  severity: medium
  status: open
  promoted: 2026-08-15 — the story 4.4 review pass that found this escalated CRITICAL on an unrelated intent gap before any of its findings could be applied ("no patches were applied and no ledger entries were written -- the intent gap makes every lower finding moot"); recovered from the run's own raw session log (`.bmad-loop/runs/20260814-202334-1831/logs/4-4-mason-environment-check-review-2.log`) during `/bmad-loop-resolve` so it is not lost when the run directory is eventually cleaned up.

### DW-4-4-6

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: FR-28 — the sole FR Story 4.4 realizes (`epics.md:114`, `:1210`) — is cited nowhere in the package (`grep -rn "FR-28" src tests` returns 0 hits, vs. 17 for FR-25 and 20 for FR-27). Every new Story 4.4 docstring/comment (`errors.py:812,870,928`; `condalock.py:70,242`; `cli.py:1371`) cites FR-25/FR-27/FR-29 — the sibling story's FRs, copied wholesale.
  evidence: Review-verified via direct grep against the delivered code.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-7

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `CondaLockCheckResult`'s `stdout` field docstring (`condalock.py:242-253`) claims it "mirror[s] `CondaLockResult`'s own identical fields **and rationale**" — but that rationale ("a failure investigated outside a live terminal needs diagnostic text, not a bare returncode integer") is false for `check()`: the field is structurally always empty, since `stderr=None` inherits and this module's own docstring states conda-lock writes every progress/diagnostic line to stderr and nothing to stdout on either outcome.
  evidence: Review-verified by direct inspection of `condalock.py`.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-8

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `EnvironmentCheckTimeoutError`'s docstring (`errors.py:944-946`) says `timeout` is "the number of seconds that **elapsed** before the child was killed"; the call site (`condalock.py:389`) actually passes `resolved_timeout`, the configured *limit*. Copied verbatim from `EnvironmentLockTimeoutError` (`errors.py:781-782`), which carries the identical pre-existing inaccuracy — the new class propagated it rather than correcting it.
  evidence: Review-verified by direct inspection; the sibling class's own copy is pre-existing (not introduced by this story).
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-9

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: the after-invocation lockfile read misattributes engine-side corruption to the user. Both reads call `_read_content_hash(temp_lockfile_path, lockfile_path)` (`condalock.py:367,387`), and the helper names the *second* argument in its error message. The before-read already proved the caller's file parses, so an after-read failure (conda-lock killed, or `$TMPDIR` filling mid-rewrite and truncating the temp copy) can never be the caller's file's fault — yet it raises `EnvironmentLockfileMalformedError` naming the user's own intact lockfile and prescribing regeneration.
  evidence: Review-verified by direct inspection of the two call sites and the helper's error-naming behavior.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-10

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `check()`'s argv test asserts via `argv.index("-f")`/`argv.index("-p")` against single-element inputs only (`_MANIFEST_PATHS = ("environment.yml",)`, `platforms = ("linux-64",)`), so it would pass even if `check()` emitted only the first manifest or platform of a multi-element list. `check()` re-implements `lock()`'s repetition loops rather than sharing them, and `lock()` has its own multi-element regression tests (`test_lock_with_multiple_platforms_repeats_dash_p_in_order`, `test_lock_with_multiple_manifests_repeats_dash_f_in_order` — `test_engines_condalock.py:219,234`) that `check()` has no equivalent of.
  evidence: Review-verified by direct inspection of the test suite.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-11

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `environment lock`'s dispatch returns `EXIT_OK` unconditionally (`cli.py:1381-1388`), so a failed solve that wrote no lockfile still exits 0 — the exact opposite policy to the `returncode`-projection this story's own first review pass added to `check`'s dispatch, whose own comment argues "a CI gate must not green-light on its own internal failure." Pre-existing (Story 4.3); the two sibling verbs on one noun now disagree with each other.
  evidence: Review-verified by direct inspection of both dispatch branches in `cli.py`.
  severity: medium
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-12

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: every conda-lock diagnostic names the temp copy's path, not the user's real lockfile (e.g. `.../tmp/mason-condalock-check-vedwraei.yml is missing a version`). The path is one the user never supplied, the `finally` block unlinks it before they can inspect it, and nothing maps the message back to their own file. Contrasts with `_read_content_hash`'s own errors, which are careful to name `lockfile_path` (the user's real path) — the child process's own output is never re-mapped at all. A consequence of this story's temp-copy design (necessary so the user's file is never mutated).
  evidence: Review-verified by direct inspection of the temp-copy flow and cleanup.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).

### DW-4-4-13

- source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`
  summary: `--format json` emits no JSON at all on any typed-error path. `main()`'s `except MasonError` handler (`cli.py:1456-1460`) prints `str(exc)` to stderr and returns `EXIT_FAILED` with stdout left empty — but the frozen spec's own intent-contract states a JSON envelope on both the success path (`:1202-1204`) and a typed-error path (`:1206-1208`) of the same contract.
  evidence: Review-verified by direct inspection of `main()`'s exception handling against the frozen spec's own stated contract.
  severity: low
  status: open
  promoted: 2026-08-15 — see DW-4-4-5's promoted note (same recovery).
