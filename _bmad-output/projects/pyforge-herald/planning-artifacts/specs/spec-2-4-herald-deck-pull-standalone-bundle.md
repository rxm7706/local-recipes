---
title: 'Authored-source pull — standalone bundle'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `bridge-protocol.md` § *Authored-source pull* names a third CAP-2 target: a
Design-authored "standalone bundle" (e.g. `Warden Infographic standalone.html`) that lands at
`src/marp/<slug>-infographic-standalone-<date>.html`, **superseding** any `marp --html` render of the
infographic (a `marp --html` render is only the fallback when no bundle exists). Stories 2.1/2.3 pull
the prototype and Marp sources; there is still no way to pull the standalone bundle.

**Approach:** Add `deck_pipeline.pull_standalone_bundle`, the third and last CAP-2 leaf, reusing the
identical read/etag/decode/atomic-write/state-record loop (`_pull_and_land`) with its own remote path
(`f"{persona} Infographic standalone.html"`) and landing path
(`src/marp/<slug>-infographic-standalone-<date>.html`). Wire it into `herald deck pull` as
`--target standalone`.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.pull_standalone_bundle(transport, *, slug, repo_root, commit=False, state_path=None, exporter=None, committer=None, now=None) -> PullResult`.
- Remote path: `f"{persona} Infographic standalone.html"`, `persona = _persona_from_slug(slug)` --
  matches `bridge-protocol.md`'s own worked example (`Warden Infographic standalone.html`).
- Local landing path: `presentations/<slug>/src/marp/<slug>-infographic-standalone-<date>.html`.
- Artifact key: `"standalone-bundle"`. No local-prove step (same as Story 2.3 -- authored-source pulls
  never extract/build); `exporter.export(slug=..., repo_root=...)` runs after a real change.
- `--commit` behaves identically to Stories 2.2/2.3's.
- `herald deck pull <slug> --target standalone` dispatches to `pull_standalone_bundle`.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- **`pull_standalone_bundle` never itself renders a `marp --html` fallback.** The
  bundle-supersedes-marp-render logic is `deck-export`'s own responsibility (an external, already-
  existing pixi task this story does not modify): `deck-export` checks for the bundle file's presence
  at the fixed canonical landing path and prefers it over rendering `marp --html` when found. Herald's
  job is narrower and structurally simpler -- always write to that one fixed path when a bundle is
  available, then invoke `deck-export` -- and the write always completes (atomic, synchronous)
  strictly before `deck-export` runs, so there is no window where `deck-export` could observe a
  partially-written bundle. This module contains no branch that renders HTML from Markdown itself.
- No new artifact-kind lookup table beyond the one fixed `standalone-bundle` key -- there is exactly
  one standalone bundle per deck, unlike the three Marp-source kinds.
- No live MCP call in this package's own test suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Unchanged | `read_file` answers `{unchanged: true}` for `Warden Infographic standalone.html` | no write, no state update, no export | No error |
| Changed | real body | body written to `presentations/pyforge-warden/src/marp/pyforge-warden-infographic-standalone-<date>.html`; state etag key `standalone-bundle` updated; `exporter.export` runs | No error |
| `--target standalone` | CLI | dispatches to `pull_standalone_bundle` | No error |
| Not seeded | no state entry | refused before any transport call | `HeraldError` |
| Truncated / no-body | as Story 2.1 | refused before write | `HeraldError` |
| `--commit`, real change | as Story 2.2 | staged + committed | No error |
| `--commit`, unchanged | as Story 2.2 | never commits | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit --
  `STANDALONE_BUNDLE_ARTIFACT_KEY`, `pull_standalone_bundle`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck pull --target`
  gains the `standalone` choice; `_pull_operation` dispatches it.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- the I/O matrix's
  `pull_standalone_bundle` rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_pull.py` -- edit -- the `--target standalone`
  dispatch row.

## Design Notes

**Why "supersedes marp --html" needed no code here, and why that is a deliberate, not a missed,
scope boundary.** The bridge-protocol text describes an *outcome* ("the bundle supersedes any
marp --html render"), not a step this CLI performs. `deck-export` (untouched by this story) already
owns rendering the infographic from Marp sources, and the natural, minimal way for it to prefer an
operator-authored bundle over its own render is to check whether one already exists at the bundle's
fixed path before falling back -- exactly the check-then-render sequence the task framing warns
against racing. Because `pull_standalone_bundle` always finishes writing (atomically, synchronously)
before it invokes `deck-export`, there is no concurrent-write race for `deck-export` to lose: by the
time `deck-export` runs, the bundle is either fully present (this pull just landed it, or a prior pull
did) or fully absent (never pulled) -- never partially written. Verified by inspection: this module
has exactly one write site per artifact (`_atomic_write_text`, already crash-safe), and the
`exporter.export` call is sequenced strictly after it returns, in the same synchronous call stack, on
one thread.

**Judgment call: this story does not modify `deck-export` itself.** The task's own framing scoped
Epic 2 to Herald's `pull` surface; `deck-export`'s own bundle-vs-marp preference logic is out of this
package entirely (it lives in the repo's Marp/pixi tooling, `docs/specs/presentation-deck.md`'s own
territory) and was not touched, read in full, or modified here. If `deck-export` does not already
implement that preference correctly, that is a `deck-export` defect, not a `pull_standalone_bundle`
one -- flagged as a verification gap in this story's own Verification section rather than silently
assumed away.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green.
- `ruff format --check` / `ruff check` clean on every file this story touches.
- `herald deck pull --help` -- shows `--target standalone`.

**Verification gap (not closed by this story):** whether `deck-export` (external, unmodified) actually
implements "prefer the bundle file over a marp --html render when the bundle is present at its fixed
path" was NOT verified by reading `deck-export`'s own implementation in this session -- out of this
story's stated code map. If a future story or the orchestrating session's review finds `deck-export`
does not honor that preference, the fix belongs to `deck-export`, not this module.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must run one real
`herald deck pull pyforge-warden --target standalone` against the live endpoint (the Warden Design
project has this exact bundle per `bridge-protocol.md`'s own worked example), confirming the remote
path convention matches the real file name and that the subsequent `deck-export` run picks up the
landed bundle over a `marp --html` render.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read focused specifically on the bundle-supersedes-marp-render logic (checking for
bundle existence BEFORE deciding to fall back, not racing), per this effort's own closeout brief.

- `[none]` No defects found. Verified directly:
  - `grep -n "marp\|--html"` over `deck_pipeline.py` shows every hit is a docstring, comment, or a
    path-string literal (`"src" / "marp" / ...`) -- this module contains no branch that shells `marp`
    or renders HTML from Markdown. The "supersedes" behavior is entirely `deck-export`'s (unmodified,
    out of this module's code map, documented as a verification gap above rather than silently
    assumed correct).
  - `test_pull_standalone_bundle_write_completes_before_export_runs` proves the ordering directly: a
    `ReadingExporter` fake reads the bundle file back from disk at `export()` call time and gets the
    just-written body, not stale/missing content -- the write is synchronous and precedes the export
    call in the same call stack, so there is no window for `deck-export` to observe a partial file.
  - `grep` sweep for MCP tool-name literals: clean, same shape as every prior story in this epic (only
    `transport.<method>(...)` calls, docstrings, and error-message strings).
- `addressed_findings`: 0. `followup_review_recommended: true` retained; this story's own Verification
  section already names the one real gap this session could not close (whether `deck-export` itself
  correctly implements the bundle preference), and the deferred live-MCP proof is the other.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 390 passed, 2 skipped
(was 382 passed, 2 skipped after Story 2.3; +8 net new tests: 8 in `test_deck_pipeline.py`, plus 1 in
`test_cli_pull.py`). `ruff format --check` / `ruff check` clean on every file this story touches (17
pre-existing findings elsewhere in the package, untouched by this epic, remain out of scope per Story
1.6's own precedent note).
