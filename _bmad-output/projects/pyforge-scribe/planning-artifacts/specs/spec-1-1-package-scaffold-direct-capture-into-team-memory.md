---
title: 'Package scaffold + direct capture into team memory (Story 1.1)'
type: 'feature'
created: '2026-07-25'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: 'bbe44fa5af21f205640eb6001909c5729a6cb7a8'
final_revision: '09c851f4c6'
---

<intent-contract>

## Intent

**Problem:** `pyforge-scribe` does not exist as a package yet, and there is no checked-in team-memory store — a decision captured by one agent/developer stays siloed in their own user-local auto-memory, causing the duplicated-rediscovery pain that motivated this product.

**Approach:** Scaffold `src/shared/packages/pyforge-scribe/` as a pixi workspace member mirroring the shipped `pyforge-warden` package exactly, scaffold the checked-in `.claude/memory/` tree (`feedback/`/`project/`/`reference/` + starter `MEMORY.md` + `README.md`), and implement `scribe capture` as a real, direct (non-promotion) append-only write path into `.claude/memory/`, with `scribe graph compile`/`scribe recall` present as harmless typer stub subcommands so the CLI's top-level shape never changes between epics.

## Boundaries & Constraints

**Always:**
- Package layout, pixi wiring (feature block, environment, tasks), and `pyproject.toml` shape mirror `pyforge-warden`'s precedent exactly (AD-7, architecture Structural Seed).
- `.claude/memory/<type>/*.md` frontmatter is `name` (kebab-case slug), `description` (one-line), `metadata.type` ∈ `{feedback, project, reference}` — the CURRENT live auto-memory shape (verified against on-disk files and this session's own memory-writing instructions), not the architecture doc's flatter shorthand. Isolate this in one serialize/deserialize pair so future upstream drift touches one place.
- `scribe capture` writes ONLY under `.claude/memory/<type>/` — no other path (AD-2, FR-7).
- Capture is append-only / no-clobber: a slug collision appends a numeric suffix rather than overwriting (AD-1).
- Each successful capture adds exactly one new index line to `MEMORY.md`, under the matching `## Feedback`/`## Project`/`## Reference` H2 section, format `- [Title](type/slug.md) — description`.
- Zero required network calls (AD-6) — capture is pure local file I/O.
- `graph compile [--nightly]` / `recall <query>` subcommands parse args and exit 0 with an explicit "not yet implemented" stderr notice; they must not attempt real compile/recall logic or touch any file.
- `pixi run -e pyforge-scribe pyforge-scribe-test` passes and is the bmad-loop policy's verify command.

**Block If:** none — the schema-nesting and `--type decision` ambiguities below were resolved against verifiable live ground truth, not left open.

**Never:**
- Do not implement `--promote`, user-local-memory reading, team-voice rewrite, or pointer-stub logic — Stories 1.3/1.4 own that.
- Do not implement real graph-compile or recall logic, or pick a `GraphStore` engine — Epic 2 (Story 2.1+, AD-5) owns that.
- Do not create a `.claude/skills/team-memory/` skill — superseded by the CLI per the PRD's D-1/addendum decision.
- Do not edit root `CLAUDE.md` — Story 1.2, human-edited.
- Do not add a `promoted:` field to entries this command writes — that is a user-local pointer-stub concept (Story 1.4), not applicable to direct team-memory captures.
- Do not expose `--name`/`--description` override flags — Story 1.1's CLI surface is exactly `--type`/`--text`, matching the epic's own acceptance criteria; name/description are always derived from `--text`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `scribe capture --type project --text "ADR-005b: in-house gateway replaces LiteLLM"` | New file `.claude/memory/project/<slug>.md` with valid frontmatter + body; one new line under `## Project` in `MEMORY.md` | exit 0 |
| Invalid type | `--type decision` (not in the taxonomy) | No file written | typer validation error naming valid choices, exit 2 |
| Slug collision | Second capture whose derived slug matches an existing file | New file written with a `-2` suffix; original file untouched | exit 0, no data loss |
| Missing `--text` | `scribe capture --type feedback` | No file written | typer required-option error, exit 2 |
| `graph compile` stub | `scribe graph compile --nightly` | No file anywhere is touched | prints "not yet implemented" to stderr, exit 0 |
| `recall` stub | `scribe recall "why did we pick X"` | No output implies a real answer | prints "not yet implemented" to stderr, exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/` -- packaging precedent to mirror exactly (`pyproject.toml`, `pixi.toml`, `.gitignore`, `README.md` shape)
- `pixi.toml` (root) `[feature.pyforge-warden.*]` block (~L1041-1087) -- template for the new `[feature.pyforge-scribe.*]` block; environments block (~L142-143) -- add the `pyforge-scribe` entry there
- `docs/specs/claude-team-memory.md` Story 1 (L170-194) / Story 8 (L286-311) -- exact `.claude/memory/` scaffold + `README.md` acceptance criteria this story fulfills
- `_bmad-output/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md` § Structural Seed, AD-1/2/3/5/6/7 -- binding file-tree + rules
- `~/.claude/projects/<encoded-repo-path>/memory/*.md` (e.g. `feedback_python_test_convention.md`, `project_pyforge_warden.md`) -- ground truth for the CURRENT nested frontmatter shape

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-scribe/pixi.toml` -- create `[package]` + `[package.build.backend]` (pixi-build-python) + host/run-dependency tables mirroring warden's -- establishes the pixi-build workspace member
- [x] `src/shared/packages/pyforge-scribe/pyproject.toml` -- create hatchling-backed manifest, `[project.scripts] scribe = "pyforge.scribe.cli:main"`, deps `typer>=0.27.0`, `pydantic>=2.13.4` -- CLI entry point + build config
- [x] `src/shared/packages/pyforge-scribe/README.md`, `.gitignore` -- mirror warden's shape and "build skeleton" status framing -- packaging hygiene parity
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/__init__.py` -- `__version__`, minimal public exports (AD-7) -- public surface
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` -- `CaptureRecord` Pydantic model (`id`, `type`, `name`, `description`, `text`, `supersedes`, `captured_at` UTC, `source`) plus `to_frontmatter()`/`from_frontmatter()` isolating the on-disk schema -- single swap point for schema drift; establishes the model the whole epic depends on (architecture Technical Decisions), even though `supersedes`/`id`/`source`/`captured_at` are not yet consumed by anything outside this module in Wave 1
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/capture.py` -- direct-capture write path: derive slug + description from `--text`, no-clobber write under `.claude/memory/<type>/`, append one `MEMORY.md` index line; accepts an injectable memory-root path (never hardcodes the repo tree) -- AD-1/AD-2/FR-7 write-boundary logic lives in exactly one module
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- typer app: `capture` (real, calls `capture.py`), `graph compile [--nightly]` and `recall <query>` (stub subcommands) -- FR-14 top-level contract
- [x] `src/shared/packages/pyforge-scribe/src/pyforge/scribe/py.typed` -- empty marker -- typing support
- [x] `src/shared/packages/pyforge-scribe/tests/unit/test_capture.py` -- cover the I/O matrix above using `tmp_path` as the injected memory root (never the real repo tree) -- verification + write-boundary proof
- [x] `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- typer `CliRunner` smoke tests for all three subcommands incl. the two stubs -- FR-14 contract proof
- [x] `pixi.toml` (root) -- add `[feature.pyforge-scribe.dependencies]` (path dep + hatchling/python-build/pytest), `pyforge-scribe-test`/`-build-conda`/`-build-dist`/`-build` tasks, and the `pyforge-scribe` `no-default-feature` environment entry, mirroring the warden block -- FR-15, bmad-loop verify command
- [x] `.claude/memory/feedback/.gitkeep`, `.claude/memory/project/.gitkeep`, `.claude/memory/reference/.gitkeep` -- commit the empty structure -- legacy Story 1 AC
- [x] `.claude/memory/MEMORY.md` -- starter index: header explaining purpose + the 200-line truncation convention, empty `## Feedback`/`## Project`/`## Reference` sections -- FR-2, legacy Story 1 AC
- [x] `.claude/memory/README.md` -- Purpose, relationship to user-local auto-memory, the verified current schema, `MEMORY.md` format, team-relevance test (day-1-contributor heuristic), promotion workflow (note: arrives Story 1.3), pointer stubs (note: arrives Story 1.4), when-to-prune -- legacy Story 8 AC

**Acceptance Criteria:**
- Given a clean checkout, when `pixi run -e pyforge-scribe pyforge-scribe-test` runs, then the built `pyforge-scribe` conda package installs into the lean env and the full test suite passes.
- Given no `.claude/memory/` directory exists, when this story lands, then `feedback/`, `project/`, `reference/` exist (each committed via `.gitkeep`) alongside a starter `MEMORY.md` and a `README.md` documenting the schema and the team-relevance test.
- Given `scribe capture --type project --text "ADR-005b: in-house gateway replaces LiteLLM"` is run from the repo root, when it completes, then a new file exists under `.claude/memory/project/` with `name`/`description`/`metadata.type` frontmatter and `MEMORY.md` has exactly one new line referencing it.
- Given the same capture command is run a second time with the same text, when it completes, then a second, distinct file is written (numeric-suffixed slug) rather than overwriting the first.
- Given `scribe graph compile --nightly` or `scribe recall "<query>"` is run, when either completes, then no file under `.claude/memory/`, the future graph store, or anywhere else is modified, and the process exits 0 having printed an explicit not-yet-implemented notice.
- Given any `scribe capture` invocation (successful or rejected), when the write boundary is inspected, then no file outside `.claude/memory/**` and the Scribe package's own source tree was touched.

## Spec Change Log

## Review Triage Log

### 2026-07-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 2, low 2)
- defer: 0
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` `CaptureRecord.to_frontmatter()` emitted an unquoted `name:` YAML scalar, so text like `"404"`/`"2026-07-25"`/`"yes"` round-tripped as `int`/`date`/`bool` for any standards-compliant reader instead of `str`. Reproduced with real YAML parsing. Fixed: quote+escape `name` the same way `description` already was; `from_frontmatter()` unescapes it symmetrically. Regression test added.
  - `[high]` `[patch]` `capture()`'s two-step write (record file, then unlocked read-modify-write of `MEMORY.md`) was neither atomic nor concurrency-safe. Reproduced with 20 threads racing `capture()`: only 7 of 20 index lines survived and several calls raised after a section heading got corrupted mid-write. Fixed: the whole write is now one cross-platform-locked critical section (stdlib `fcntl`/`msvcrt`, no new dependency), and `MEMORY.md`'s section is validated to exist *before* the record file is written (removes the orphan-file-on-failure case too). Regression test reproduces the original 20-thread race and asserts zero lost entries.
  - `[medium]` `[patch]` A bare `---` line inside captured `--text` produced a file with three `---` delimiters, ambiguous for any naive whole-file frontmatter splitter (and `from_frontmatter()` had no production caller to prove it worked at all). Fixed: added `models.parse_capture_file()`, which locates the frontmatter boundary via the first two `---`-only lines rather than a naive split, with a regression test capturing text containing an embedded horizontal rule and round-tripping it correctly.
  - `[medium]` `[patch]` `cli.py`'s `_MEMORY_ROOT` comment asserted "always run from the repo root" but nothing enforced it; running from the wrong cwd silently materialized a disconnected `.claude/memory/` tree. Fixed: `capture()` now requires `memory_root` to already exist (Story 1.1 itself scaffolds it) and raises a clear, CLI-surfaced error otherwise instead of auto-creating it; only the `<type>/` subdirectory is still auto-created. Regression test + CLI test added.
  - `[low]` `[patch]` Blank/whitespace-only `--text` was silently accepted, writing a generically-named, empty-description entry. Fixed: `capture()` rejects blank text with a clear `ValueError`, surfaced by the CLI as exit code 2. Regression test added at both the `capture()` and CLI layers.
  - `[low]` `[patch]` `capture()` created the type subdirectory before validating `capture_type`, so a direct (non-CLI) caller passing an invalid type could leave a stray directory on disk before the error fired. Fixed: `capture_type`/blank-text/`memory_root`-existence are all validated at the top of `capture()`, before any filesystem mutation. Regression test added.
  - (Self-caught during the patch pass, not from either reviewer: the new lock file for the concurrency fix would otherwise have landed inside `.claude/memory/` — violating both `capture()`'s own "writes only under memory_root" contract and the legacy spec's Story 1 AC that `.claude/memory/`'s `.gitignore` stays untouched. Moved the lock file to the OS temp dir, keyed by `memory_root`'s resolved path, before any of the above landed.)
- rejected_findings (for record; not actioned):
  - `README.md`'s `d43899c1cb` citation "unrelated to team-memory rediscovery" — verified the commit; it's the one that added the now-duplicated `CLAUDE.md` §"BMAD ↔ conda-forge-expert integration" section, which is plausibly exactly the origin of the dated duplication pain. Citation is defensible, not confidently wrong.
  - `.claude/memory/README.md`'s "mechanical, never a translation" portability claim — the frontmatter schema genuinely is byte-compatible (AD-3's actual claim); differing physical file location (subdirs vs. flat prefix) is directory routing, not a field-level translation. Not confidently a defect.
  - Tracked story-spec promotion missing from this diff — this repo's convention promotes a story spec to `planning-artifacts/specs/` *after* merge, not during dev; not yet due.
  - `MEMORY.md`'s 200-line cap asserted but not enforced in code — explicitly out of scope per the PRD's FR-2 ("no tooling gate required" in Wave 1); reviewer lacked that context.
  - `_truncate()` can split a multi-codepoint grapheme cluster mid-truncation for exotic Unicode `--text` — real but cosmetic-only (affects only the preview `description` field, not the stored body); fixing correctly needs a grapheme-cluster library, disproportionate to a v1 scaffold.

## Design Notes

- **Frontmatter schema was verified against live ground truth, not the architecture doc's shorthand.** AD-3/FR-1 describe the target schema in prose as flat `name`/`description`/`type`. The actual, currently-produced auto-memory files (this session's own memory-writing instructions, and the most-recently-written on-disk entries such as `feedback_python_test_convention.md` and `project_pyforge_warden.md`) nest `type` under a `metadata:` key instead — older files use the flat form, showing the upstream schema has already drifted once. Scribe targets the CURRENT nested form because that is what a Story 1.3+ promotion will actually need to read/write for byte-compatible parity; `models.py`'s frontmatter (de)serializer isolates this choice into one function so a future upstream change touches one place, not every caller.
- **`--type decision` in the epic's example acceptance criterion is illustrative content, not a literal enum value.** FR-8/AD-3 fix the type taxonomy at `{feedback, project, reference}`; the epic's own parenthetical ("or the type-matching subdirectory per FR-8") already signals this. This spec's worked example uses `--type project` for the same ADR-flavored text.
- Capture's body is the raw `--text` verbatim — no team-voice rewrite, no Why:/How-to-apply structuring. That enforcement is Story 1.3's promotion-boundary concern (FR-4); direct capture is deliberately fast and unstructured.
- `name`/`description` are always derived from `--text` (slug: lowercase, non-alphanumeric → hyphens, truncated; description: `--text` truncated to a reasonable one-line length) — no override flags in this story, keeping the CLI surface exactly `--type`/`--text` as specified.

## Verification

**Commands:**
- `pixi run -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green; this is the bmad-loop policy's verify command
- `pixi run -e pyforge-scribe scribe capture --type project --text "smoke test entry"` -- expected: new file under `.claude/memory/project/`, one new `MEMORY.md` line
- `pixi run -e pyforge-scribe scribe graph compile --nightly` and `pixi run -e pyforge-scribe scribe recall "test"` -- expected: exit 0, stub notice on stderr, no filesystem changes

**Manual checks (if no CLI):**
- Diff `.claude/memory/` after the smoke-test capture above to confirm the write boundary (nothing outside the tree changed).

