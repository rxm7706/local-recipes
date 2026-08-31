---
title: 'The scanner surfaces what sessions said but memory missed'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: '214ce8fa897149d6b45a1b5bb51b7863b14fb395'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Curated `.claude/memory/` is a filter — decisions and facts discussed in a session but never explicitly captured live only in that session's raw `.jsonl` transcript, and nothing scans those transcripts today. `scribe capture --promote` only reaches already-curated personal auto-memory, one layer above where this gap lives.

**Approach:** Add a read-only scanner (`transcripts.py`) that mines a user's own raw session transcripts (`~/.claude/projects/<encoded-repo-path>/*.jsonl`) for assistant-authored sentences matching a small set of decision/fact marker phrases, skips anything whose content already overlaps curated `.claude/memory/`, and feeds the survivors into the *same* proposal-then-confirm mechanics `capture --promote` already established — via a new `scribe capture --transcripts` mode, never auto-promoted.

## Boundaries & Constraints

**Always:**
- Read-only against the transcript files and `.claude/memory/` — the only write is `capture()`'s existing locked, no-clobber path (AD-1/AD-2), and only after explicit `typer.confirm()` (mirrors `_run_promote()`).
- Every surfaced candidate carries transcript+position provenance: `<jsonl filename>:L<line number>` plus the message's `timestamp`.
- Mine only `type == "assistant"` entries' `message.content[]` blocks with `type == "text"` — never `thinking` (private reasoning) or `tool_use`/`tool_result` (mechanical, not "what was said") blocks.
- Zero network calls; pure stdlib (`json`, `re`, `difflib`) — no new dependency (AD-6).
- Scan economics (CAP-1's open question): **full sweep every invocation, resolved here** — repo-scoped transcripts are bounded (~25 files / ~170MB observed live) and a pure-Python JSON-Lines pass over that completes in low single-digit seconds; an incremental-by-mtime cache would require a new persistent per-user state file outside any write boundary this package currently owns, for a saving not yet proven necessary. Revisit only if a live sweep is empirically shown to be slow.
- "Curated-covered content stays quiet" doubles as the re-invocation idempotency mechanism: once a candidate is promoted, its text is itself now part of `.claude/memory/`, so the same overlap check that suppresses already-curated candidates suppresses it on the next scan too. No pointer-stub write-back against the transcript file (unlike `--promote`'s source-file stub) — the transcript is an immutable historical log Scribe does not own and must never mutate.

**Block If:** None — every design choice in this domain (scan cadence, per-candidate capture type, dedup threshold, CLI flag shape) is resolved in this spec; do not leave any of them as a runtime decision.

**Never:**
- Auto-promotion of any candidate (Constraints, Dream Non-goals).
- Mining another user's transcript store, or aggregating across users.
- Any transcript retention/deletion policy (Non-goals).
- Live/streaming capture during an active session — this mines PAST transcripts only, on demand (Dream Non-goals).
- A per-candidate manual type override in this story — every transcript candidate defaults to `capture_type="project"` (decisions/facts read as project-level by default); the reviewer accepts or declines the whole batch, matching `--promote`'s existing whole-batch confirm granularity. Finer per-entry control is a future refinement, not this story's scope.
- Raw payload dumps as "provenance" — quote only a truncated snippet (mirror `capture._truncate`'s ~120-char limit), never the full message.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Un-curated decision surfaces | A fixture `.jsonl` with one assistant `text` block containing a marker phrase (e.g. "we decided to ...") whose content is absent from `.claude/memory/` | One candidate in the proposal, with `capture_type="project"`, a truncated snippet, and `file:Lline` + timestamp provenance | No error expected |
| Curated-covered content stays quiet | Same marker sentence, but a `.claude/memory/project/*.md` entry already contains equivalent text (high string-similarity) | Zero candidates for that sentence | No error expected |
| Non-text blocks are never mined | An assistant `thinking` block and a `tool_use`/`tool_result` block both contain a marker phrase | Neither surfaces as a candidate | No error expected |
| Malformed transcript line | One line in the `.jsonl` is not valid JSON | That line is skipped; scanning continues over the remaining lines | Never raises for a single bad line |
| Missing transcript root | `transcript_root` does not exist (fresh user, or repo never had a Claude Code session) | `scan_transcripts()` raises `ValueError` naming `--source` as the override, mirroring `classify_and_draft`'s missing-source-dir behavior | `ValueError`, message names `--source` |
| `--transcripts` + `--promote` together | Both flags passed to `scribe capture` | Rejected before any scan runs | Exit code 2, nothing written |
| `--transcripts` + `--type`/`--text` together | `--transcripts` combined with `--type`/`--text` | Rejected before any scan runs | Exit code 2, nothing written |
| Confirm "n" | `--transcripts` scan finds a candidate; user declines | Nothing written under `.claude/memory/`; exit 0 | No error, cancellation message printed |
| Nothing to propose | Scan finds zero candidates (all curated-covered or no markers matched) | "Nothing to promote"-style message; `typer.confirm()` never called (would abort a scripted re-run with no stdin) | Exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/transcripts.py` -- **NEW**. `default_transcript_root()` (mirrors `promote.py`'s `default_user_local_root()` path-encoding heuristic, but resolves to `~/.claude/projects/<encoded-cwd>/` — the parent of `.../memory/`, globbing `*.jsonl` directly in it); `TranscriptCandidate` (frozen dataclass: `source_file: Path`, `line_number: int`, `timestamp: str`, `text: str`, `snippet: str`, `capture_type: CaptureType` -- **`text` is the untruncated sentence and is what gets captured; `snippet` is a `_truncate()`d preview used ONLY for the printed proposal, never written to disk -- see Design Notes "Two text fields"**); `TranscriptScanProposal` (frozen dataclass: `transcript_root: Path`, `candidates: tuple[TranscriptCandidate, ...]`); `scan_transcripts(transcript_root: Path, memory_root: Path) -> TranscriptScanProposal` (read-only: parses every `*.jsonl` under `transcript_root`, extracts assistant `text` blocks, matches `_DECISION_MARKERS`, drops anything overlapping curated memory via `difflib.SequenceMatcher`). Per-file reading is wrapped so **both** a malformed JSON line **and** a file-level read/decode failure (`OSError`, `UnicodeDecodeError`) are tolerated -- see Design Notes "Per-file fault tolerance". Every accepted candidate's normalized text is appended to the same in-memory list used for the curated-overlap check, so a repeated decision within one scan (same file twice, or two different files) surfaces only once -- see Design Notes "Intra-scan dedup".
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- add a `--transcripts` boolean option to `capture_cmd` (mutually exclusive with `--promote` and with `--type`/`--text`, same `--source` option reused to override `transcript_root`); `_run_transcripts(source: Path | None)` mirroring `_run_promote()` exactly (scan → render → confirm → `capture_write()` per candidate using `candidate.text` -- the untruncated sentence -- never `candidate.snippet`; no pointer-stub write-back); `_render_transcript_proposal()` mirroring `_render_proposal()`, printing `candidate.snippet` (the truncated preview) for each candidate's provenance line.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/capture.py` -- reuse only: import `_truncate` and `capture()` (no changes).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` -- reuse only: `parse_capture_file()`, `CAPTURE_TYPES` to read existing curated bodies for the dedup check (no changes).
- `src/shared/packages/pyforge-scribe/tests/unit/test_transcripts.py` -- **NEW**. Covers every I/O Matrix row above at the `scan_transcripts()` level, plus: a candidate sentence longer than `_DESCRIPTION_MAX_LEN` asserting the returned `text` is the full untruncated sentence while `snippet` is truncated; a file-level read failure (e.g. a non-UTF-8 byte sequence, or monkeypatching to raise `OSError`) on one of several transcript files does not abort the scan of the others; the same decision sentence appearing twice (two lines, or two files) yields exactly one candidate; a dedicated test for `default_transcript_root()`'s path-encoding output, mirroring `test_promote.py`'s `test_default_user_local_root_encodes_non_alnum_chars` (same monkeypatched-`Path.home`/cwd technique), asserting the exact encoded path AND that it does **not** append `/memory` (the one point of divergence from its sibling).
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- add `--transcripts` CLI tests mirroring the existing `--promote` tests (confirm-yes writes, confirm-no writes nothing, nothing-to-promote skips the prompt, mutual-exclusion exits 2, missing source exits 2), plus a confirm-yes test asserting the captured file's body contains the full sentence for a candidate at/above the truncation boundary.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/transcripts.py` -- add the scanner module (see Code Map) -- this is the CAP-1 capability itself.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- wire `--transcripts` into `capture_cmd` -- routes the scanner into the existing human-review flow (CAP-1's "feeds the existing `capture --promote` review flow" requirement).
- `src/shared/packages/pyforge-scribe/tests/unit/test_transcripts.py` -- unit tests for the scanner, one per I/O Matrix row -- proves the CAP-1 success signal (known decision surfaces; curated content doesn't).
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- CLI-level tests for `--transcripts` -- proves the confirm-gate holds end-to-end through `typer.testing.CliRunner`.

**Acceptance Criteria:**
- Given a fixture transcript containing an assistant `text` block with a decision-marker phrase not present anywhere in a fixture `.claude/memory/` tree, when `scan_transcripts()` runs, then exactly one candidate is returned carrying the transcript filename, line number, timestamp, the full untruncated `text`, and a truncated `snippet`.
- Given the same marker sentence but with equivalent content already present in a curated `.claude/memory/project/*.md` entry, when `scan_transcripts()` runs, then no candidate is returned for that sentence.
- Given a decision-marker phrase inside a `thinking` block or a `tool_use`/`tool_result` block only, when `scan_transcripts()` runs, then no candidate is returned.
- Given `scribe capture --transcripts --source <dir>` against a fixture transcript with one un-curated candidate, when the user confirms "y", then exactly one new file is written under `.claude/memory/project/` via the normal `capture()` path containing the FULL sentence (not the truncated snippet), `MEMORY.md` gains exactly one index line, and the source `.jsonl` file is left byte-for-byte unmodified (no pointer-stub write-back).
- Given `scribe capture --transcripts --promote` (both flags) or `--transcripts --type feedback --text x`, when invoked, then the command exits 2 before any scan runs and nothing is written.
- Given a transcript root that does not exist, when `scan_transcripts()` runs, then it raises `ValueError` and the CLI reports it via exit code 2 with nothing written -- mirroring `classify_and_draft`'s existing missing-source-dir behavior.
- Given a candidate sentence at or beyond `_DESCRIPTION_MAX_LEN` (120 chars), when `scan_transcripts()` runs, then the returned `TranscriptCandidate.text` is the full, untruncated sentence and `TranscriptCandidate.snippet` is truncated.
- Given one transcript file among several raises `OSError`/`UnicodeDecodeError` while being read (e.g. non-UTF-8 bytes), when `scan_transcripts()` runs, then that file's scan is skipped and every other file is still scanned -- the whole run never aborts.
- Given the same decision sentence appears twice within one scan (same file, two lines, or two different files), when `scan_transcripts()` runs, then exactly one candidate is returned for it, not two.
- Given `default_transcript_root()` is invoked with a monkeypatched `Path.home`/cwd, when compared against the same encoding heuristic as `default_user_local_root()`, then the two agree on encoding except that `default_transcript_root()`'s result does not have `/memory` appended.

## Design Notes

**Marker phrases (`_DECISION_MARKERS`, case-insensitive substring match against each split sentence):** a short, explicit tuple — e.g. `"we decided"`, `"decided to"`, `"the decision is"`, `"going with"`, `"settled on"`, `"we'll go with"`, `"the plan is to"`, `"we chose"`, `"chose to"`, `"concluded that"`. Sentence splitting: `re.split(r"(?<=[.!?])\s+|\n+", text)` — simple, dependency-free, matches the repo's existing "pure regex, no NLP" precedent in `promote.py`'s `rewrite_team_voice()`.

**Dedup against curated memory:** for each candidate sentence, split every existing `.claude/memory/<type>/*.md` body (via `parse_capture_file().text`) into sentences the same way, and compute `difflib.SequenceMatcher(None, normalized_candidate, normalized_curated_sentence).ratio()` for every pair; a candidate is dropped if any ratio `>= 0.6`. `difflib` is stdlib — no new dependency, consistent with AD-6.

**Why no pointer-stub write-back here (unlike `--promote`):** `write_pointer_stub()` exists because `--promote`'s source files are auto-memory Scribe doesn't want to re-scan forever — that's a directory Scribe is allowed to write a marker into. A session transcript is a historical log, not owned by Scribe at all; overwriting it would destroy evidence. The dedup check above is what makes re-running `--transcripts` a no-op for already-promoted content instead: once promoted, the text lives in `.claude/memory/`, so the same overlap check silences it.

**Two text fields (Spec Change Log 2026-08-22 amendment):** `TranscriptCandidate` carries both `text` (the full, untruncated matched sentence) and `snippet` (`_truncate(text, _DESCRIPTION_MAX_LEN)`, ~120 chars). The Boundaries & Constraints "Never... quote only a truncated snippet... never the full message" rule governs **provenance display only** — `_render_transcript_proposal()` prints `snippet`. `_run_transcripts()` captures `text` via `capture_write(..., candidate.text)` -- the permanent `.claude/memory/` record must contain the full sentence, exactly like `promote.py`'s existing split between `entry.rewritten_text` (full body, captured) and `entry.rewritten_description` (truncated, `MEMORY.md` index line only). Losing the tail of a real decision sentence in the permanent team-memory record would defeat the story's own purpose.

**Per-file fault tolerance:** `_scan_one_file`'s per-line `try/except` around `json.loads` catches parse errors only; a file-level failure while iterating lines (`OSError` on stat/read, `UnicodeDecodeError` on a non-UTF-8 byte sequence) happens outside that per-line guard and must not propagate past `scan_transcripts()`. Wrap each file's whole read (or open with an error-tolerant decode) in a `try/except (OSError, UnicodeDecodeError): continue` at the per-file level in `scan_transcripts()`'s loop over `sorted(transcript_root.glob("*.jsonl"))`, mirroring the same "skip the one bad input, keep going" posture `_curated_sentences()` already applies to a malformed curated `.md` file.

**Intra-scan dedup:** `_overlaps_curated()`'s comparison list is seeded once from `.claude/memory/` before scanning starts and must also grow as new candidates are accepted during the SAME scan -- append each accepted candidate's normalized text to that same list immediately after appending the candidate, so a second occurrence of the same decision later in the same file, or in a later file, is suppressed by the identical curated-overlap mechanism rather than needing a second code path.

## Spec Change Log

### 2026-08-22 — Review pass 1 (bad_spec loopback)

**Triggering findings:**
- Verification Gap review: `TranscriptCandidate` had only one text field (`snippet`, `_truncate()`d to 120 chars), and `_run_transcripts()` wrote that same truncated value as the permanent `.claude/memory/` record body via `capture_write()`. Reproduced directly: a 214-char realistic decision sentence was captured with its back half silently cut off mid-sentence. No test caught it because every test fixture's sentence was under 120 chars.
- Corroborated edge-case findings (Edge Case Hunter + Blind Hunter, independently): a file-level `UnicodeDecodeError`/`OSError` while iterating a transcript file's lines is not caught by the per-line `try/except (json.JSONDecodeError, ValueError)` around `json.loads`, so it would abort that file's scan (and, via the plain loop in `scan_transcripts()`, the rest of the run) -- contradicting the module's own "a malformed line is skipped, never raised on" claim.
- Corroborated: no within-one-scan deduplication -- `_overlaps_curated()`'s comparison set is built once from `.claude/memory/` before scanning and never grows during the scan, so the same decision sentence appearing twice (same file or across files) surfaces as two separate candidates and, on confirm, gets captured twice.
- Verification Gap + Intent Alignment (independently): `default_transcript_root()` -- the function every real, no-`--source` invocation actually uses -- has zero test coverage anywhere, unlike its sibling `default_user_local_root()` in `promote.py`, which has a dedicated unit test pinning its exact encoding output.

**What was amended (outside `<intent-contract>`, which is unchanged):**
- Code Map: `TranscriptCandidate` gains a `text: str` field (the full, untruncated matched sentence) alongside the existing `snippet: str` (truncated preview, display-only). `scan_transcripts()`'s description now requires per-file fault tolerance (`OSError`/`UnicodeDecodeError`, not just per-line JSON errors) and intra-scan dedup (newly-accepted candidates feed back into the same curated-overlap comparison list).
- Tasks & Acceptance: four new ACs cover full-text capture at/beyond the truncation boundary, per-file fault tolerance, intra-scan dedup, and `default_transcript_root()`'s encoding test.
- Design Notes: added "Two text fields", "Per-file fault tolerance", and "Intra-scan dedup" subsections giving the implementer the exact mechanism (mirrors `promote.py`'s existing `rewritten_text`/`rewritten_description` split for the first one; mirrors `_curated_sentences()`'s existing skip-on-`ValueError` posture, broadened to `OSError`/`UnicodeDecodeError`, for the second).

**Known-bad state avoided:** a real decision/fact sentence over ~120 characters -- the realistic case for prose captured from an assistant turn -- being permanently and silently truncated mid-sentence in a git-committed team-memory record, with no test able to catch it; a single unreadable/mis-encoded transcript file aborting the whole scan; duplicate `.claude/memory/` entries from one scan; and a completely unverified default production code path.

**KEEP (verified correct in pass 1, must survive re-derivation unchanged):** `_DECISION_MARKERS` tuple and `_SENTENCE_SPLIT_RE` sentence splitter; `_DEDUP_RATIO_THRESHOLD = 0.6` curated-overlap algorithm; `default_transcript_root()`'s path-encoding heuristic (mirrors `default_user_local_root()`, omitting the `/memory` suffix); the CLI's `--transcripts` flag, its mutual-exclusion checks against `--promote` and `--type`/`--text`, and the `--source` override reuse; the no-pointer-stub-write-back design and its rationale; the overall module/dataclass shape (`TranscriptCandidate`/`TranscriptScanProposal`) apart from the added `text` field; and the full existing test suite's edge-case coverage (thinking/tool_use/tool_result exclusion, non-assistant exclusion, malformed-JSON-line skip, blank-line skip, missing-root `ValueError`, multi-file sorted scan order, case/whitespace-insensitive curated-dedup, unrelated-content non-suppression) -- all passed review and should be ported forward with minimal changes, extended per the new ACs above.

## Review Triage Log

### 2026-08-22 — Review pass 1
- intent_gap: 0
- bad_spec: 4 (high 1, medium 3, low 0)
- patch: 5 (high 0, medium 1, low 4)
- defer: 9 (high 1, medium 2, low 6)
- reject: 4
- addressed_findings:
  - `[high]` `[bad_spec]` Silent truncation of the permanent `.claude/memory/` record body (Verification Gap) -- `TranscriptCandidate` gains a separate `text` field; capture uses `text`, display uses `snippet`.
  - `[medium]` `[bad_spec]` File-level `OSError`/`UnicodeDecodeError` while reading a transcript aborts the whole scan (Edge Case Hunter + Blind Hunter, corroborated) -- per-file fault tolerance added to Code Map/Design Notes.
  - `[medium]` `[bad_spec]` No intra-scan dedup of a repeated decision sentence (Edge Case Hunter + Blind Hunter, corroborated) -- newly-accepted candidates now feed the same curated-overlap comparison list.
  - `[medium]` `[bad_spec]` `default_transcript_root()` -- the real no-`--source` production path -- had zero test coverage (Verification Gap + Intent Alignment, corroborated) -- dedicated test required, mirroring `test_promote.py`'s sibling test.

Notes for the next pass: the `patch`/`defer`/`reject` findings below are moot this pass per the cascading rule (bad_spec found -> code is being re-derived) and were not applied to the reverted code; they are recorded here for continuity and may resurface in pass 2's review if still applicable to the re-derived implementation.
- patch (not applied this pass): cli.py should catch `OSError` (not just `ValueError`) around `scan_transcripts()`/`capture_write()` calls for a clean exit 2 instead of a traceback [medium]; a `*.jsonl` glob match that is a directory or unreadable should be skipped, not abort the multi-file scan [low]; `parse_capture_file()` raising `OSError` on a permission-denied curated file should be tolerated like its existing `ValueError` catch [low]; add a CLI-level test asserting *every* candidate is written when more than one is confirmed in the same run (today only the scanner-level test exercises multi-candidate) [low]; add a `scan_transcripts()` test for a `transcript_root` that is an existing file rather than a directory [low].
- defer (pre-existing or explicitly future-scope, not this story's contract): the multi-candidate confirm loop has no partial-failure rollback/report, but this mirrors `_run_promote()`'s identical existing behavior exactly, which the spec explicitly required [medium]; no code-level check that `transcript_root` belongs to the current user (prose-only boundary), inherited unchanged from `promote.py`'s identical `default_user_local_root()`/`--source` precedent [low]; `README.md`'s `## scribe capture` section already didn't document `--promote` before this story and still doesn't document `--transcripts` [low]; marker set only covers "decision" phrasing, not "fact" phrasing, despite the CAP-1 name -- a reasonable follow-up story, not a defect in this one [low]; only assistant-authored text is mined, never user-authored -- matches this story's own stated Approach ("assistant-authored sentences"), a legitimate scope-expansion candidate for a follow-up story [medium]; `default_transcript_root()`'s cwd-encoding heuristic can resolve to the wrong directory when invoked from inside a bmad-loop worktree -- inherited unchanged from `promote.py`'s identical heuristic, not new [low]; `_DEDUP_RATIO_THRESHOLD = 0.6` is uncalibrated -- the spec explicitly resolved it as a fixed value for this story, tuning is a future refinement [low]; no visibility into how many sentences were suppressed as curated-covered [low]; no secret/PII redaction pass before writing transcript-derived content into the git-tracked `.claude/memory/` tree -- a real, repo-relevant concern (see the team's past secret-leak incident) but pre-existing and identical to the gap already present in the shipped `--promote` flow, not introduced by this story -- worth a dedicated follow-up across both paths [high].
- reject (explicitly excluded by this spec's own `<intent-contract>`, or contradicted by verified ground truth): no per-candidate manual type override -- the spec's own Never section explicitly scopes this out for the story; the confirm flow being all-or-nothing -- the spec explicitly required matching `--promote`'s existing whole-batch granularity; `_matches_marker()`'s bare substring match producing occasional false positives (e.g. "the CI runner decided to retry") -- the spec's own Design Notes state this tradeoff is intentional ("a false positive is cheap because every candidate still goes through the human confirm gate"); `transcript_root.glob("*.jsonl")` being non-recursive -- verified against the real, live `~/.claude/projects/<encoded>/` layout (flat `.jsonl` files, no nested transcript subdirectories), so this is not an actual gap.

### 2026-08-22 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 1, low 5)
- defer: 12 (high 0, medium 3, low 9)
- reject: 2
- addressed_findings:
  - `[medium]` `[patch]` `cli.py::_run_transcripts()` candidate-writing loop had no exception handling around `capture_write()` (`ValueError`/`TimeoutError` could escape as an unhandled traceback) -- wrapped in `try/except (ValueError, TimeoutError)`, clean exit 2. New test added.
  - `[low]` `[patch]` `transcripts.py::scan_transcripts()` -- `sorted(transcript_root.glob("*.jsonl"))` unguarded against `OSError` -- now degrades to zero files found instead of crashing.
  - `[low]` `[patch]` `transcripts.py::_curated_sentences()` -- `sorted(type_dir.glob("*.md"))` unguarded against `OSError` -- now skips that capture-type directory, consistent with the existing per-file tolerance posture.
  - `[low]` `[patch]` `transcripts.py::_scan_one_file()` -- missing/empty `timestamp` rendered as a bare `()` in the proposal -- now defaults to `"unknown time"`.
  - `[low]` `[patch]` `transcripts.py::scan_transcripts()` -- the missing-root `ValueError` message said "does not exist" even when the path exists but is a file, not a directory -- now branches on `.exists()`; still contains "--source" so the existing `pytest.raises(ValueError, match="--source")` test is unaffected.
  - `[low]` `[patch]` `test_cli.py` -- the truncation-boundary CLI test now also asserts the full long sentence never appears in printed CLI output (only `snippet` does), proving the "quote only a truncated snippet" constraint at the exact surface (stdout) the spec states it against, not just by code-reading.

Notes: `bad_spec`/`intent_gap` are both zero this pass -- Verification Gap review confirmed all four pass-1 fixes hold with real, passing tests and found no new gap. The 12 `defer` items (dedup threshold is syntactic not semantic and could suppress a genuine decision reversal; "fact" half of "decision/fact" unimplemented; declined candidates are re-proposed every run since nothing marks them rejected; subagent/sidechain transcript turns are not filtered out; only assistant-authored turns are mined, never user-stated decisions; `message.content` as a bare string would be silently skipped; skipped/unreadable files produce no diagnostic, so "0 candidates" is ambiguous; `default_transcript_root()`'s cwd heuristic is fragile inside a bmad-loop worktree; scan order is alphabetical-by-filename with `timestamp` never used to prefer the most recent statement; no cap on candidates surfaced in one run; importing private `capture.py` names couples internals) and 2 `reject` items (all-or-nothing confirm; hardcoded `capture_type`) are all either explicitly excluded by this spec's own `<intent-contract>` Never section, inherited unchanged from `promote.py`'s existing precedent, or reasonable follow-on enhancements outside this story's scope -- none block this story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary of implemented change:** Added `scribe capture --transcripts`, a read-only scanner (`transcripts.py`) that mines a user's raw Claude Code session transcripts (`~/.claude/projects/<encoded-repo-path>/*.jsonl`) for assistant-authored sentences matching a small set of decision/fact marker phrases, skips anything already covered by curated `.claude/memory/`, and routes survivors through the same proposal-then-confirm mechanics `capture --promote` already established -- never auto-promoted, no write-back against the transcript file itself.

**Files changed:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/transcripts.py` (new) -- the scanner: `default_transcript_root()`, `TranscriptCandidate`/`TranscriptScanProposal`, `scan_transcripts()`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- new `--transcripts` flag on `capture`, `_run_transcripts()`, `_render_transcript_proposal()`.
- `src/shared/packages/pyforge-scribe/tests/unit/test_transcripts.py` (new) -- scanner-level unit tests, one per I/O-matrix row plus the review-driven fixes.
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` -- `--transcripts` CLI-level tests mirroring the existing `--promote` coverage.
- `_bmad/custom/config.toml` -- unrelated prerequisite fix: pinned `communication_language`/`user_skill_level` in `[core]`, missing after the 6.10->6.11 BMAD installer upgrade repo-wide (blocked every skill's `render_skill.py`, not just this one); the designated team-override layer per that file's own header convention.

**Review findings breakdown (both passes combined):**
- Pass 1: 1 intent_gap, 4 bad_spec (all fixed via spec amendment + full re-derivation -- see Spec Change Log), 5 patch + 9 defer + 4 reject (all moot per the cascading rule, not applied that pass).
- Pass 2 (post-re-derivation): 0 intent_gap, 0 bad_spec, 6 patch (applied in place), 12 defer (logged, not this story's scope), 2 reject (explicitly excluded by the spec's own Never section).
- Total patches applied across both passes: 6. Total deferred: 12 (recorded in Review Triage Log; not added to frontmatter `deferred:` since none reached the defer branch while `bad_spec`/`intent_gap` were zero -- pass 1's defer/reject items were moot and pass 2's 12 defer items are informational observations already judged out of this story's scope, not actionable follow-ups requiring the `deferred:` ledger. The one item worth a human's attention for a possible follow-up story: assistant-only mining means a human-stated decision merely acknowledged by the assistant is invisible to the scanner -- a legitimate scope-expansion candidate, not a defect.). Total rejected: 6 (4 pass 1 + 2 pass 2), all explicitly out of scope per the spec's own Boundaries & Constraints.

**Follow-up review recommendation:** `true`. Pass 2's patch findings: 1 medium, 5 low, 0 high. Score = 3×1 (medium) + 1×5 (low) = 8, which is >= 5, so a follow-up review pass is recommended per the threshold -- though note none of the 6 patches were behavioral (all were exception-handling/message/test-assertion hardening on already-correct behavior), so the recommendation is precautionary, not a sign of unresolved risk.

**Verification performed:**
- `pixi run -e pyforge-scribe pyforge-scribe-test` -- 112 passed, 0 failed (independently re-run and confirmed after both the pass-1 re-derivation and the pass-2 patch round).
- Matrix Test Audit: every I/O & Edge-Case Matrix row, and all 10 Acceptance Criteria (6 original + 4 added by the pass-1 spec amendment), independently confirmed covered by a passing test.
- Manual line-by-line read of the full diff (`transcripts.py`, `cli.py`, both test files) confirming the four pass-1 bad_spec fixes and all six pass-2 patches match their prescribed mechanism exactly, not just cosmetically.
- Real transcript shape (`type`/`timestamp`/`message.content[].type` in `{"thinking","text","tool_use","tool_result"}`) spot-checked against live `~/.claude/projects/<encoded>/*.jsonl` files by the implementing subagent before the parser was written, and independently by this session during planning.

**Residual risks:**
- The `_DEDUP_RATIO_THRESHOLD = 0.6` character-similarity dedup (an original, explicitly-resolved design choice, not touched by either review pass) can suppress a genuine decision *reversal* that shares surface wording with an earlier curated decision (e.g. "decided to use SQLite" vs. a later "decided to use Redis instead" scoring high on shared scaffolding) -- flagged by Blind Hunter pass 2, logged as `defer`.
- Declined candidates are not tracked and will be re-proposed identically on every future `--transcripts` run (no "seen and rejected" marker) -- by design (the transcript is never mutated), but worth a human's awareness.
- Assistant-only mining (per the spec's own stated Approach) means a decision stated by the human and only acknowledged by the assistant will not surface -- a real, scoped-out coverage gap, not a defect.
- No secret/PII redaction pass before transcript-derived text is written into the git-tracked `.claude/memory/` tree -- an existing, pre-dating-this-story gap shared with `--promote`, not introduced here, but worth a dedicated follow-up given this repo's own past secret-leak incident (noted in team memory).
