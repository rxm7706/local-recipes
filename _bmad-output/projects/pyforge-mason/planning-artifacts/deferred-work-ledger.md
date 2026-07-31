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
