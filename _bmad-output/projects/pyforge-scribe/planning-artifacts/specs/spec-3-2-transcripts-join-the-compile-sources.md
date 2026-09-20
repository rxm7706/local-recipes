---
title: 'Transcripts join the compile sources'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      A transcript node's citation/id is derived only from the source file's
      basename (not a path relative to transcript_root), so two different
      transcript files sharing a basename under different subdirectories
      would collide into the same node id.
    evidence: |-
      Corroborated independently by two review passes (Blind Hunter and
      Edge Case Hunter). Currently unreachable: scan_transcripts() globs
      only *.jsonl directly in transcript_root (non-recursive), and
      default_transcript_root() always resolves to one flat directory, so
      no subdirectory structure can exist under it today. A real fix would
      require changing the citation format away from this story's own
      intent-contract, which explicitly fixed it as
      "<jsonl filename>:L<line>" with no directory path, matching Story
      3.1's established provenance convention -- so it is out of this
      story's scope, not a defect in what was built here.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:_read_transcript_surface
    severity: low
  - summary: >-
      The transcript surface is the only compile surface with no cost
      bound, and this story puts it on the unattended nightly path: every
      `scribe graph compile` now reads every *.jsonl under the transcript
      root whole into memory and runs an O(candidates x curated-sentences)
      difflib comparison, with no file cap, byte cap, timeout, or
      mtime-incremental pass.
    evidence: |-
      Raised independently by all four review layers. Measured on this
      machine: the production root for the owning repo
      (~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes)
      holds 27 files totalling 631MB, roughly 4x the 161MB the owning Dream
      cites. Every other surface has a ceiling (`max_commits=100`,
      `_MAX_DOC_TEXT_CHARS=20_000`, `timeout=30` on `git log`); this one has
      none. Story 3.1 only ever drove `scan_transcripts()` interactively.
      Out of scope on this story's own intent authority, not a defect in
      what was built: `Block If: None` asserts every design choice is
      resolved, and the Approach mandates reusing `scan_transcripts()`
      exactly, so bounding it means either changing Story 3.1's scanner or
      pre-filtering ahead of it -- both new design decisions. The spec's own
      frontmatter open question ("Scan economics over 161MB+: incremental by
      transcript mtime vs full sweeps -- decide at 3.1") was never decided
      at 3.1 and is still open.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:_read_transcript_surface
    severity: medium
  - summary: >-
      The `pyforge-scribe/spec-pyforge-scribe` spec-surface baseline is
      stale for 12 files, and the spec's .memlog.md carries no provenance
      entry for Story 3.1 or 3.2, so the governed-surface reconcile for
      Epic 3 has never been done.
    evidence: |-
      `python -m pyforge.doctor.sources spec-surface` reports 12
      drift-presumed warnings for pyforge-scribe/spec-pyforge-scribe. Six
      are this story's own files (compile.py, models.py, recall.py,
      test_compile.py, test_recall.py, test_supersession.py); two are Story
      3.1's, never stamped (transcripts.py, test_transcripts.py); four
      predate Epic 3 (README.md, pixi.toml, pyproject.toml, graph_store.py).
      Deliberately NOT reconciled inside this review pass: the remedy the
      detector names is a spec-scoped `--write-baseline --spec
      pyforge-scribe/spec-pyforge-scribe`, which stamps all twelve at once
      and would silently absorb six files of drift this story neither caused
      nor verified -- exactly the failure mode the repo's own "three checks
      before a scoped stamp, never a bare --write-baseline" convention
      warns against. Wants its own scoped reconcile (memlog entry naming the
      paths, then the stamp), the same shape as commit b513e29aee did for
      marshal Story 11.4 on this branch.
    location: >-
      scripts/.spec-surface-baseline.json + _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts/.memlog.md
    severity: low
  - summary: >-
      `recall.answer()` ranks candidates by token overlap and tie-breaks on
      node id ascending, never consulting `valid_from`, so between two
      equally-overlapping nodes the alphabetically-earlier id wins -- which
      for date-ordered session filenames is usually the OLDER, since-reversed
      statement.
    evidence: |-
      Verified in `recall.py::answer()`:
      `scored.sort(key=lambda pair: (-pair[0], pair[1].id))`, and its own
      docstring states the id tie-break is deliberate, "for reproducibility".
      Pre-existing Story 2.x recall behaviour, not introduced here -- but this
      story is what makes it bite: transcript nodes are the first surface
      where two nodes routinely make contradictory claims about the same
      decision across time, and (per the already-rejected supersession
      finding) `_apply_supersession()` has no path to invalidate a transcript
      node, so the superseded statement stays `is_current` indefinitely.
      Fixing it means choosing a recency policy for ties, which is a new
      design decision for recall, not a defect in what this story built.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py:answer
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Epic 2's knowledge-graph compile (`compile.py`) reads five named surfaces (`.claude/memory/`, `.memlog.md`, git history, CHANGELOGs, retros) but ignores Story 3.1's transcript scanner entirely, so an un-curated decision/fact that only ever surfaced in a raw session transcript is invisible to `scribe recall` and to any future lost-artifact recovery query -- the exact gap Epic 3 exists to close.

**Approach:** Add a sixth `_read_transcript_surface()` to `compile.py` that calls Story 3.1's `scan_transcripts()` against the same curated `memory_root`, turns each un-curated `TranscriptCandidate` into a `GraphNode(kind="transcript")` citing `<jsonl filename>:L<line>` (Story 3.1's own provenance format), and extends `recall.py`'s citation-resolvability gate to recognize that new citation shape -- so these nodes are actually queryable, not just stored.

## Boundaries & Constraints

**Always:**
- `compile.py` interacts with storage only via the `GraphStore` port (AD-5); no new direct engine import.
- Reuse Story 3.1's `scan_transcripts()`/`default_transcript_root()` exactly -- no second transcript-parsing implementation (Epic 3's own Cross-Story Dependencies: "the scanner must exist before its output can be registered as a compile source").
- A missing/unreadable transcript root degrades to a warning and zero transcript nodes, same as every other optional surface (the existing git-absent precedent) -- never aborts the compile.
- Citation format is exactly `<jsonl filename>:L<line number>` -- no directory path -- matching Story 3.1's own established provenance convention.
- Node `text` carries the candidate's full untruncated sentence, never the truncated `snippet` -- same "full record, truncated display only" rule Story 3.1 established for its own captured records.
- A transcript citation is not required to resolve to a still-existing file on disk (transcripts are per-user local and can be pruned/rotated outside Scribe's control) -- extend `recall.py`'s existing `commit:<sha>` precedent (format-checked only, never re-resolved against `.git`) to the new citation shape, rather than requiring a live file the way repo-tracked citations do.

**Block If:** None -- every design choice here (which candidates to index, citation shape, id disambiguation, the recall-gate extension) is resolved in this spec.

**Never:**
- No second decision-marker/dedup implementation in `compile.py` -- always delegate to `scan_transcripts()`.
- No raw full-transcript dump as a compile source -- only the same curated-filtered candidate set Story 3.1's scanner already produces (Epic 3: "content already covered by curated memory must stay quiet"; the owning Dream: "must not raw-dump transcript content ... 161MB of tool-call noise").
- No new CLI flag on `scribe graph compile` -- production wiring calls `default_transcript_root()` exactly like `_run_transcripts()` already does; no `--source` override at the compile layer for this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Un-curated transcript decision surfaces | Fixture `.jsonl` with one assistant sentence matching a decision marker, absent from curated memory | One `kind="transcript"` node; `text` = full sentence; `citation` = `<file>:L<line>` | No error |
| Curated-covered content isn't double-indexed | Same sentence already present in curated `.claude/memory/` | No transcript node for it (already indexed once, via the memory surface) | No error |
| Missing/unreadable transcript root | `transcript_root` does not exist | Compile still succeeds; zero transcript nodes; exactly one warning naming the transcript surface | Never raises |
| Two candidates on one transcript line | One message with two decision-marked sentences | Two distinct transcript nodes with two distinct ids | No error |
| Recall over a transcript-derived fact | Compiled graph contains one transcript node whose tokens match a query | `scribe recall` returns it grounded, citing `<file>:L<line>` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` -- `GraphNodeKind` (line 124) gains `"transcript"`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` -- import `scan_transcripts`, `default_transcript_root` from `pyforge.scribe.transcripts`; `compile_graph()` (line 84) gains an optional `transcript_root: Path | None = None` param, defaulting to `default_transcript_root()` when `None` (mirrors the existing `store`/`store_path` injection pattern already used for testability); new `_read_transcript_surface(memory_root, transcript_root, warnings) -> list[GraphNode]` (mirrors `_read_git_surface`'s try/except-then-warn shape at line 269), wired into the surface loop after the existing five and before `_apply_supersession` (line 131). A per-`(source_file, line_number)` occurrence counter disambiguates multiple candidates on one line into distinct ids: `transcript:<file>:L<line>` for the first, `transcript:<file>:L<line>:1`, `:2`, ... for repeats -- keyed off the candidate's own file+line identity (not a global running index), so a brand-new unrelated transcript file appearing later never perturbs an already-assigned id. `valid_from` parses `candidate.timestamp` via `datetime.fromisoformat()`, falling back to the source file's own mtime -- deliberately NOT `datetime.now()` (unlike the git-surface's existing unparseable-date fallback), because `datetime.now()` here would break `compile_graph()`'s own byte-identical-rerun guarantee for any candidate lacking a timestamp.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` -- `_citation_is_resolvable()` (line 98) gains a transcript-citation branch (`re.compile(r".+\.jsonl:L\d+$")`), format-checked only -- mirrors the existing `commit:<sha>` branch exactly (checked by regex shape, never re-resolved against `.git`), since a transcript file is per-user/local and its absence on a given machine must not permanently blackhole an otherwise-valid graph node from `scribe recall`.
- `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` -- pass an explicit, empty `transcript_root=tmp_path / "no-transcripts"` to every EXISTING `compile_graph(...)` call. This file never `chdir`s, so `default_transcript_root()`'s real `Path.cwd()`-encoded fallback would otherwise resolve to THIS repo's own live `~/.claude/projects/.../*.jsonl` transcripts on a developer machine, making the existing exact `node_count`/id-list assertions non-deterministic. Plus new transcript-surface tests (see Tasks).
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` -- new test for the transcript-citation branch, mirroring the existing `test_commit_citation_is_resolvable_if_well_formed_sha`.
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- one new end-to-end `graph compile` test reusing the existing `_scaffold_transcript_entry`/`_assistant_transcript_line` fixtures (already present from Story 3.1's CLI tests), monkeypatching `pyforge.scribe.compile.default_transcript_root` to point at a tmp fixture directory -- never the real home directory.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` -- add `"transcript"` to `GraphNodeKind` -- CAP-2's new node kind.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` -- add `_read_transcript_surface()` + `transcript_root` param, wire into `compile_graph()` -- the compile-source registration itself (CAP-2).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` -- extend `_citation_is_resolvable()` -- makes the registered nodes actually queryable (AD-8), not merely stored.
- `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` -- isolate existing tests from ambient real transcripts + add new surface tests (happy path, curated-stays-quiet, missing-root warning, same-line disambiguation, idempotent rerun).
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` -- transcript-citation resolvability test.
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- end-to-end `graph compile` test through the real CLI.

**Acceptance Criteria:**
- Given a fixture transcript with one un-curated decision sentence and an empty curated memory tree, when `compile_graph()` runs, then exactly one `kind="transcript"` node is produced whose `text` is the full sentence and whose `citation` is `<filename>:L<line>`.
- Given that same sentence already present in curated `.claude/memory/`, when `compile_graph()` runs, then no transcript node is produced for it (it is indexed once only, via the memory surface).
- Given a missing or non-existent transcript root, when `compile_graph()` runs, then it still succeeds, contributes zero transcript nodes, and appends exactly one warning naming the transcript surface.
- Given two decision-marked sentences within the same transcript line, when `compile_graph()` runs, then two distinct transcript nodes are produced with two distinct ids.
- Given an unchanged transcript fixture, when `compile_graph()` runs twice in a row, then the resulting `GraphStore` output is byte-identical (idempotency, mirrors the module's existing rerun guarantee).
- Given a compiled graph containing a transcript node whose tokens match a query, when `scribe recall <query>` runs, then it returns that node grounded, citing its `<filename>:L<line>` provenance -- proving AD-8's gate no longer silently discards every transcript-derived fact.

## Spec Change Log

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 1, low 2)
- defer: 1 (low 1)
- reject: 11
- addressed_findings:
  - `[high]` `[patch]` `test_supersession.py`'s 5 `compile_graph()` call sites lacked `transcript_root=` isolation, letting the real `~/.claude/projects/.../*.jsonl` transcripts leak into supersession tests (flaky, and blind to a real transcript-surface regression) -- added `transcript_root=tmp_path / "no-transcripts"` to all 6 call sites (one test calls it twice).
  - `[medium]` `[patch]` `_transcript_valid_from()`'s mtime-fallback `stat()` call was unguarded against the transcript file being deleted/rotated between scan and stat, which would abort the whole compile -- wrapped in `try/except OSError`, falling back to `datetime.now(timezone.utc)`; added a dedicated test exercising the missing-timestamp mtime-fallback branch, previously uncovered.
  - `[low]` `[patch]` `test_transcript_surface_happy_path_produces_one_node` didn't distinguish `node.title` (candidate.snippet) from `node.text` (candidate.text) since the fixture sentence was short enough that both were byte-identical -- replaced with a >120-char sentence so truncation actually occurs, and added `node.title != node.text` plus exact-value assertions for both.
  - `[low]` `[patch]` The transcript-surface warning read as an actionable misconfiguration even for the ordinary, expected "no transcripts yet on this machine" case -- reworded to read as informational/benign for that case.

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 1, medium 0, low 2)
- defer: 0
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` `_transcript_valid_from()`'s exception handling was too narrow and could crash the entire `compile_graph()` run on a single malformed transcript line: `fromisoformat(candidate.timestamp)` caught only `ValueError`, but a non-string `timestamp` (e.g. a raw JSON number) raises `TypeError`; the mtime fallback caught only `OSError`, but `fromtimestamp()` can also raise `OverflowError` for an out-of-range mtime. Reproduced the `TypeError` crash directly before patching. Widened both except clauses to `(ValueError, TypeError)` and `(OSError, OverflowError)`; added `test_transcript_surface_non_string_timestamp_falls_back_to_file_mtime_without_raising` reproducing the exact crash input. Independently found by all three automated reviewers (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer) and confirmed by direct reproduction both before and after the fix.
  - `[low]` `[patch]` `cli.py`'s `graph_compile()` command docstring still described only the original five compile surfaces, unlike every other docstring this story updated (`compile.py`, `models.py`, `recall.py`) -- updated to mention the transcript surface.
  - `[low]` `[patch]` `models.py`'s `GraphNode` docstring opened with "citation is always resolvable to a real repo artifact," self-contradicted by the transcript-citation sentences this story added immediately after it -- reworded the lead sentence so it no longer contradicts the transcript case.
  - `reject` (9, verified before rejecting): no CLI `--source` override for `graph compile` (explicitly forbidden by this spec's own `Never:` clause); transcript citations being format-checked-only vs. other kinds' live-file check ("inconsistent") (explicitly the behavior this spec's `Boundaries & Constraints` specifies); basename-only citation collision risk (duplicate of the collision risk already recorded in this spec's frontmatter `deferred:` list); duplicated test-helper functions across `test_compile.py`/`test_cli.py` (matches this codebase's existing per-file-local-helper convention, e.g. `test_recall.py`'s own `_node()`); two pre-existing CLI tests claimed to leak the real `~/.claude/projects/...` transcript root (verified false -- both already `monkeypatch.chdir(tmp_path)`, so `default_transcript_root()` resolves to a nonexistent path and degrades deterministically to zero transcript nodes); missing multi-transcript-file test coverage and missing a test combining multi-candidate-per-line with idempotent rerun (this story's I/O matrix is fully covered per the Matrix Test Audit; additional coverage beyond the matrix is a suggestion, not a defect); a wording mismatch between the spec/epics text and the actual five pre-existing compile surfaces regarding `docs/dreams/` (already acknowledged as a pre-existing, out-of-scope gap in this spec's own Design Notes); an observation that curated-dedup correctness rests on Story 3.1's own heuristic threshold (the reviewer's own report states this is not a violation of this story's scope).

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10 (high 1, medium 2, low 7)
- defer: 2 (medium 1, low 1)
- reject: 15
- addressed_findings:
  - `[high]` `[patch]` `_transcript_valid_from()` returned a NAIVE datetime for any transcript timestamp carrying no UTC offset (`"2026-08-20T12:00:00"`), while every other surface's `valid_from` is tz-aware UTC -- so one graph could hold both, and any cross-node comparison (sorting, an AD-4 bi-temporal filter) raised `TypeError: can't compare offset-naive and offset-aware datetimes`. Reproduced directly before patching. Now normalized: a naive parse is read as UTC, matching the mtime fallback. New `test_transcript_surface_naive_timestamp_is_normalized_to_utc` asserts the value, asserts every node on the graph is aware, and sorts them.
  - `[medium]` `[patch]` An existing-but-UNREADABLE transcript root produced zero nodes AND zero warnings -- indistinguishable from "nothing decision-shaped was said" -- because `scan_transcripts()` swallows the `OSError` from its own glob. This contradicts the intent's own `Always` clause ("a missing/**unreadable** transcript root degrades to a **warning** and zero transcript nodes"). Reproduced with `chmod 000`. Added an explicit listing probe in `_read_transcript_surface`; new `test_transcript_surface_unreadable_root_warns_and_contributes_zero_nodes`.
  - `[medium]` `[patch]` The transcript-surface warning forwarded `scan_transcripts()`'s `ValueError` verbatim, whose text ends "pass `--source` to point at the correct user-local session-transcript directory" -- but `--source` exists on `scribe capture --transcripts`, NOT on `scribe graph compile`, which this story's own `Never` clause forbids giving one. The unattended path was telling operators to reach for a flag that command does not accept. Extracted `_transcript_unavailable_warning()`, which re-derives the reason (does not exist / is not a directory / is not readable) instead of forwarding the advice; new `test_transcript_surface_warning_does_not_advertise_a_flag_compile_lacks`.
  - `[low]` `[patch]` `_TRANSCRIPT_CITATION_RE` was `.+\.jsonl:L\d+$`, whose `.+` also admitted `nested/dir/x.jsonl:L1` and `../../../etc/passwd.jsonl:L1` -- contradicting the intent's own "no directory path" format clause -- and because that branch short-circuits the `is_file()` check, any such citation was declared resolvable WITHOUT existing. Tightened to a bare filename (`[^/\\:]+\.jsonl:L\d+`; the `$` was also dead under `fullmatch`). New 5-case parametrized `test_malformed_transcript_citation_is_not_waved_through`.
  - `[low]` `[patch]` Verification gap: the PRIMARY `_transcript_valid_from()` branch (the entry's own ISO-8601 timestamp) was unpinned -- the only two `valid_from` assertions both *expect* the mtime fallback, so disabling `fromisoformat()` outright left the whole suite green, and every transcript node could have been silently dated by its session file's mtime instead. `test_transcript_surface_happy_path_produces_one_node` now asserts the exact ISO value and that it differs from the file's mtime.
  - `[low]` `[patch]` Verification gap: the documented `(source_file, line_number)` id keying was unpinned -- every id test used ONE file with ONE line, for which a global running index yields identical ids, so replacing the counter with `enumerate(proposal.candidates)` also left the suite green. New `test_transcript_surface_ids_are_keyed_by_file_and_line_not_a_global_index` uses two files.
  - `[low]` `[patch]` `_read_transcript_surface`'s docstring (and this spec's matching Design Note) claimed the keying "keeps an already-assigned id stable as new, unrelated transcript files accumulate over time." Verified over-broad: `scan_transcripts()` dedups repeated sentences across files in sorted-filename order, so the same sentence in a new earlier-sorting file re-homes the node (`session-z.jsonl:L1` -> `session-a.jsonl:L1`). Both now state the accurate, narrower property.
  - `[low]` `[patch]` `TranscriptCandidate`'s docstring said `snippet` is "never written to disk" -- falsified by this story, which persists it as the transcript `GraphNode.title`. Reworded to "display only, never the record body," naming the compile surface explicitly.
  - `[low]` `[patch]` `compile.py`'s module docstring quoted AD-1 ("100% derived and re-computable ... with the same result") with nothing scoping it, but five of the six surfaces are repo artifacts and the sixth is a per-user, per-machine tree outside the repository -- so it now reads as repo-determinism it no longer has. Added a paragraph stating reproducibility is per-machine and why that is by design.
  - `[low]` `[patch]` `test_no_optional_surfaces_present_still_succeeds` was loosened to `all(("git" in w or "transcript" in w) for w in result.warnings)`, a near-tautology that holds for essentially any warning either surface could emit. Tightened to pin the transcript warning count exactly.
  - Every patch was mutation-checked: reverting each fix individually makes its own new test fail, and all 6 reverts were verified to fail before restoring. Suite: **130 passed** (121 pre-pass).
  - `defer` (2): the unbounded transcript scan now on the unattended nightly path (631MB / 27 files measured on this machine; out of scope on the intent's own `Block If: None` + "reuse `scan_transcripts()` exactly", and the spec's own "scan economics" open question was never decided at 3.1); and the stale `pyforge-scribe/spec-pyforge-scribe` surface baseline + missing Epic 3 `.memlog.md` provenance entry (deliberately not stamped here -- a spec-scoped `--write-baseline` would absorb 6 files of drift this story neither caused nor verified).
  - `reject` (15, each verified before rejecting): `Path.home()` raising `RuntimeError` with `HOME` unset and aborting the compile (**verified false** -- `Path.home()` falls back to the passwd DB; the compile succeeded with a warning); three pre-existing CLI tests said to leak the real `$HOME` (**prior pass's rejection premise re-verified and it holds** -- all three `monkeypatch.chdir(tmp_path)`, so the encoded root is nonexistent and degrades deterministically); adding an ordinal/offset so a citation is unique per node, and re-establishing AD-8 by `stat`-ing the transcript file (both contradict the intent's explicit citation-format and format-checked-only clauses); capping node `text` length for "pointers over payloads" (the intent's `Always` clause requires the FULL untruncated sentence in `text`); the human-confirm gate being bypassed / adding a confidence marker (registering the candidate set unchanged IS the intent's Approach); `default_transcript_root()` keying off `Path.cwd()` rather than `repo_root` (the intent mandates calling it exactly as `_run_transcripts()` does, and production wiring passes `repo_root=Path.cwd()`); a live transcript being appended mid-compile breaking byte-identical rerun, and adding a settle-window/mtime skip for it (inherent to every live surface including git; the AC is about an unchanged fixture, and a settle window is a new design decision); `_apply_supersession` not resolving transcript-node targets, and not de-duplicating transcript content against the memlog/CHANGELOG/commit surfaces (the intent's dedup requirement is against curated memory only); an unreadable individual FILE inside a readable root warning nothing (the intent's clause names the transcript *root*; the per-file skip is Story 3.1's own documented behavior); `recall.py`'s "two operators ... always get the identical answer" being falsified (**verified false as a finding** -- the claim is explicitly scoped to "the same compiled graph file's content," which still holds); the missing `docs/dreams/` compile surface (already recorded in this spec's own Design Notes as pre-existing and out of scope; previously rejected); transcript-JSONL test helpers duplicated across test files (matches this codebase's per-file-local-helper convention; previously rejected).

### 2026-08-22 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 0, medium 3, low 4)
- defer: 1 (medium 1)
- reject: 21
- addressed_findings:
  - `[medium]` `[patch]` Verification gap: the `:L<line>` component of every transcript citation and id was entirely unpinned -- all fifteen transcript fixtures in the package put their decision on line 1 of a one-line file, so hardcoding `citation = f"{name}:L1"` in `compile.py` left the suite at **130 passed**. Production transcripts are long multi-turn sessions; under that regression every decision after the first in a file collapses onto one id and is silently overwritten by `upsert_node()` (node loss, not a visible error), while `scribe recall`'s `[source: <file>:L<line>]` provenance points at the wrong line and still passes the format-only resolvability check. New `test_transcript_surface_citation_carries_the_real_line_number` uses a 4-line fixture with decisions on lines 3 and 4, pinning the exact id/citation set and asserting neither picks up the `:N` same-line occurrence suffix.
  - `[medium]` `[patch]` Verification gap: `_transcript_valid_from()`'s mtime-`stat()` guard -- the `except (OSError, OverflowError)` that exists precisely so a transcript pruned or rotated between `scan_transcripts()` returning and the stat cannot abort the whole compile -- was never exercised. Narrowing it to `except ():` left the suite at **130 passed**, so the never-abort contract could be regressed back to the crash review pass 2 patched. New `test_transcript_surface_source_file_rotated_before_stat_does_not_abort_compile` monkeypatches the scanner to unlink each candidate's source file before returning, asserting the compile completes and still yields a tz-aware-dated node.
  - `[medium]` `[patch]` `test_transcript_surface_unreadable_root_warns_and_contributes_zero_nodes` (added in pass 3) reds whenever the suite runs as root: `chmod(0o000)` does not deny directory listing to uid 0 (DAC is bypassed), and is inert on Windows, so no `OSError` is raised, no warning is produced, and all three assertions fail. Root is a common CI-container default, so the test would have failed on the configuration rather than on a regression. Added a `pytest.mark.skipif` guard on `win32` / `geteuid() == 0` naming the reason; verified inert at uid 1000 (the test still runs and passes, zero skips).
  - `[low]` `[patch]` The unreadable-root probe ran unconditionally *after* `scan_transcripts()`, so a root removed in between -- the same rotate-mid-compile race the mtime fallback guards -- made `iterdir()` raise, discarded candidates that had already been read successfully, and mislabelled them `does not exist -- expected when this machine has no session transcripts`. Reproduced directly (1 real candidate in, 0 nodes out, plus a false warning). Candidates are proof the root was listable, so the probe now runs only when the scan came back empty; new `test_transcript_surface_scanned_candidates_survive_a_root_pruned_mid_compile`.
  - `[low]` `[patch]` `_TRANSCRIPT_CITATION_RE` used `\d+`, which in Python also matches non-ASCII decimal digits -- so `session-a.jsonl:L١٢` was declared resolvable *without existing*, the exact short-circuit hole pass 3 tightened `.+` for. Reproduced (`_citation_is_resolvable(...) is True` against a nonexistent root). Tightened to `[0-9]+` and added the case to the existing `test_malformed_transcript_citation_is_not_waved_through` parametrization.
  - `[low]` `[patch]` `transcripts.py`'s `_DECISION_MARKERS` note justified its loose substring matching with "false positives -- acceptable because every candidate still goes through the human confirm gate before anything is written." This story falsifies that as an unconditional property: `_read_transcript_surface()` registers the same candidate set unattended, with no gate. Same class as the three docstring contradictions pass 3 patched (`TranscriptCandidate.snippet`, `GraphNode.citation`, `compile.py`'s AD-1 claim). Reworded to scope the gate to `scribe capture --transcripts` and state what a false positive costs on the compile path (one low-overlap node in a derived, re-computable graph -- never a durable curated record).
  - `[low]` `[patch]` Verification gap: `_transcript_unavailable_warning()`'s `is not a directory` branch was unexercised -- deleting it outright left the suite at **130 passed**, after which a regular file at `transcript_root` is misreported as `is not readable (ValueError)`, sending an operator to check permissions instead of the path they configured. New `test_transcript_surface_root_that_is_a_regular_file_warns_as_not_a_directory`.
  - Every patch was mutation-checked: reverting each of the five behavioural fixes individually fails exactly its own new test and nothing else (verified one at a time, then restored); the sixth is docs-only and the seventh is a skip guard verified inert on this machine. Suite: **135 passed** (130 pre-pass), via the spec's own `pixi run -e pyforge-scribe pyforge-scribe-test`.
  - `defer` (1): `recall.answer()`'s `(-overlap, node.id)` ranking never consults `valid_from`, so between two equally-overlapping transcript nodes the alphabetically-earlier session file wins -- usually the older, since-reversed decision. Pre-existing Story 2.x behaviour whose docstring calls the id tie-break deliberate; this story is what makes it bite, since transcript nodes are the first surface routinely holding contradictory claims across time and have no supersession path.
  - `reject` (21, each verified before rejecting): `Path.home()` raising `RuntimeError` with `HOME` unset (**pass 3's rejection premise re-verified and it holds** -- `Path.home()` falls back to the passwd DB); `default_transcript_root()` keying off `Path.cwd()` rather than `repo_root` (the intent mandates calling it exactly as `_run_transcripts()` does; previously rejected); an unreadable individual FILE inside a readable root warning nothing (the intent's clause names the transcript *root*; previously rejected); the unbounded transcript scan and the stale spec-surface baseline (**both already recorded in this spec's own `deferred:` list** -- not re-added); `_apply_supersession()` not reaching transcript nodes (previously rejected; the incidental ranking consequence is what was deferred instead); duplicated transcript test helpers across files (matches this codebase's per-file-local-helper convention; previously rejected twice); `_DEDUP_RATIO_THRESHOLD = 0.6` being load-bearing for an unattended index (previously rejected -- Story 3.1's own heuristic); `models.py`'s `GraphNode` docstring said to self-contradict on "always verified resolvable" (**verified false** -- the sentence's own `while` clause distinguishes the repo-artifact and format-checked cases; pass 3 already fixed the lead sentence); `cli.py::_render_transcript_proposal`'s "never the full message" said to be falsified by persisting full `text` (**verified false** -- that docstring is explicitly scoped to the confirm-prompt rendering, not to what compile persists); capping node `text` for "pointers over payloads" (the intent's `Always` clause requires the FULL untruncated sentence; previously rejected); a transcript filename containing `:` minting a node recall then refuses (the intent fixed the format literally as `<jsonl filename>:L<line>`; a name carrying the format's own delimiter falls outside it, and picking a behaviour is a new design decision -- same class as the already-deferred basename-collision item); the recall exemption being shape-keyed rather than keyed on `node.kind` (the intent names the `commit:<sha>` precedent explicitly, and that precedent is itself shape-keyed -- matching it exactly is compliance); `GraphNodeKind`'s widening having no store-level version/forward-compat guard (pre-existing `FlatFileGraphStore` design -- no version key ever existed -- and triggered only by a downgrade); marshal Story 11.4's `.memlog.md` + baseline hunks riding in this diff (a different project's governance commit, `b513e29aee`, interleaved on this branch by the orchestrator -- not caused by, and not this story's to rewrite); the warning's "expected when this machine has no session transcripts" clause being unpinned (wording, not behaviour); the new docstrings reading as a review-response log (style preference; matches the annotation convention already established in this file across three passes); replacing the ten hand-threaded `transcript_root=` kwargs with an autouse fixture (test ergonomics; the explicit kwarg is the injection this spec's own Code Map mandates); the CLI end-to-end test docstring said to overclaim by monkeypatching `default_transcript_root` (**verified** -- stubbing that function is precisely what exercises the `transcript_root=None` default-resolution branch, which is the distinction the docstring draws); the `datetime.now()` last-resort fallback appending no warning (the same tradeoff the git surface already accepts; adding one is a new design decision); missing multi-transcript-file and beyond-the-matrix coverage (previously rejected -- the I/O matrix is fully covered).

## Design Notes

**Why `recall.py` must change too:** CAP-2's own success signal is "the source registry names them with the same provenance discipline" and the epic's goal is that `scribe recall` can eventually answer "what did we discuss about X." Without extending `_citation_is_resolvable()`, every transcript node's citation would fail `(repo_root / citation).is_file()` (transcripts live outside `repo_root`, and the `:L<line>` suffix isn't a real path segment either) -- AD-8's gate would then silently discard every transcript-derived fact forever, so the graph would hold nodes `scribe recall` can never surface. Registering the source without this fix would be nominal, not real, compliance with CAP-2.

**Pre-existing gap, out of scope:** the owning Dream's own text and `epic-3-context.md` both describe Epic 2's compile sources as including `docs/dreams/`, but Story 2.2 explicitly scoped "exactly these five named surfaces" (memory/memlog/git/CHANGELOG/retro) and never implemented a dreams surface -- confirmed absent from the shipped `compile.py`. That gap predates this story, is not part of CAP-2's own capability text (which only names transcripts), and is not touched here; a future story should close it.

**Occurrence-index id scheme:** keying the disambiguation counter by `(source_file, line_number)` rather than a single global running index keeps an already-assigned id stable when a new transcript file contributes *different* content (a real production scenario -- users generate new sessions continuously); a global index would re-number every later candidate instead.

_Corrected 2026-08-22 (review pass 3):_ this note previously claimed the scheme "keeps ids stable as new, unrelated transcript files accumulate," which overstates it, and the same wording had been copied into `_read_transcript_surface`'s docstring. Verified false in one direction: `scan_transcripts()` dedups repeated sentences across files in sorted-filename order, so the SAME sentence appearing in a new, earlier-sorting file re-homes that node (`transcript:session-z.jsonl:L1` -> `transcript:session-a.jsonl:L1`). Node identity follows the surviving candidate's own file+line, not a stable per-fact key -- unlike the content-derived identity git-history (sha) and memlog (relpath) ids get. Both the note and the docstring now say so.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `edf4470ad2` (2026-08-22, "herald 15.2 / scribe 3.2 finalize: promote specs, flip ledgers"); also `71d524a90e` (2026-08-07, "herald: Story 3.2 — stale hand-mirror detection"); also `6c63b86534` (2026-08-07, "steward: Story 3.2 — a bmad-loop runner and its environment materialize together"). Ledger row `3-2-transcripts-join-the-compile-sources: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-2-dense-content-renders-as-shapes-that-fit.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-3-2-transcripts-join-the-compile-sources.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
