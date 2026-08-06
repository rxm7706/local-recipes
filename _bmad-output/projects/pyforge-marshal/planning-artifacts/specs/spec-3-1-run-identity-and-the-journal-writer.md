---
title: 'Run identity and the journal writer'
type: 'feature'
created: '2026-08-03'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: [oversized]
baseline_revision: 'c46cb584709048ee84435e7dda3624290b226f72'
final_revision: '3ed99f85ed29500b108d173613866fd1a9085b8f'
---

<intent-contract>

## Intent

**Problem:** Marshal has no run concept at all yet — `cli/gate.py`'s `--run` flag exists only as a stub reporting `MRS-GATE-005` because `core/journal.py` doesn't exist (confirmed live: `find src -iname '*journal*'` returns nothing). Without a Marshal-owned run identifier and a durable, concurrency-safe append protocol, nine loop homes sharing one canonical Tier-3 store would either collide on an externally-minted id or corrupt a shared journal file under concurrent writers — the exact incident AD-25/AD-28/AD-30 exist to prevent.

**Approach:** Add a pure `core/journal.py` (run-id minting, the journal-entry value type with its phase/intent_id invariants enforced at construction, JSON-line serialization, and the sidecar-blob threshold decision) plus two new physical primitives on the existing `FsPort`/`LocalFs` seam (`append_line` — AD-30's single-`os.write()`/`fsync` protocol — and `create_dir_exclusive` — AD-25's collision-is-a-hard-finding `mkdir`), and the JSON Schema describing one journal line. No CLI command is wired: nothing in the codebase mints an invocation yet (no `marshal run`/`marshal launch` exists — Story 3.3, `backlog`), so this story ships the buildable primitives a future launch command will call, mirroring Stories 2.4/2.5/2.6's identical "pure mechanism now, wiring later" precedent.

## Boundaries & Constraints

**Always:**
- `core/journal.py` is pure: no `os`, `subprocess`, `time`, or `pyforge.marshal.adapters` import (AD-4, enforced by the existing import-linter contract) — every clock reading, random token, and writer id is a fact the CALLER already gathered and passes in, mirroring `core/egress.py::build_gate_record`'s "already-obtained timestamp" convention exactly.
- `mint_run_id(slug: str, utc_compact: str, random_token: str) -> str` returns `f"{slug}-{utc_compact}-{random_token}"` (AD-25's `<slug>-<utc-compact>-<random>` form). `slug` is validated via `core.policy._is_valid_project_slug` (the SAME check `cli/init.py` already reuses three times — no second slug regex). `utc_compact` must match a fixed-width compact millisecond-UTC pattern (`YYYYMMDDTHHMMSSmmmZ`, e.g. `20260803T054512123Z`); `random_token` must be a non-empty lowercase-alphanumeric string. All three raise `ValueError` naming the malformed component.
- `JournalEntryId` (frozen dataclass, `order=True`): `{writer_id: str, counter: int}` — the composite id (AD-28). `writer_id` non-empty and filesystem-safe (`^[a-z0-9][a-z0-9_-]*$` — it becomes part of a sidecar blob filename, see below); `counter` a non-negative `int` (`bool` excluded, mirroring `Envelope.schema_version`'s existing bool-exclusion idiom). `order=True` gives a deterministic tie-break sort for free — AD-28's `(ts, writer_id, counter)` total order compares `ts` first at the caller/fold level; this class supplies the `(writer_id, counter)` tail in the same field order.
- `Phase` (`StrEnum`, defined in `core/journal.py` — not `core/model.py`, since nothing outside this story's own surface consumes it): `INTENT`, `OUTCOME`, `OBSERVATION` (AD-28's three-valued vocabulary).
- `JournalEntry` (frozen dataclass), built via keyword-only `build_entry(...)`: `{id: JournalEntryId, ts: str, run_id: str, kind: str, phase: Phase, story: StoryKey | None, intent_id: JournalEntryId | None, payload: Mapping[str, object]}`. `__post_init__` enforces, at construction (matching every other dataclass in this package):
  - `ts` matches the millisecond-precision UTC pattern below, validated the same two-layer way `build_gate_record` validates `timestamp` (regex spelling + `datetime.fromisoformat` zero-offset/calendar check).
  - `intent_id` is present **if and only if** `phase is Phase.OUTCOME`; absent for `INTENT` and `OBSERVATION` (AD-28's mandatory-on-outcome, absent-on-observation rule, extended to `intent` since an intent entry has nothing prior to reference).
  - `run_id`/`kind` are non-blank `str` (`.strip()` check, matching `build_gate_record`'s own `tree_revision`/`command` convention); `story`, if present, is a `StoryKey` (reuse `core.identity.StoryKey`, never a second key type); `payload` is deep-copied and `json.dumps`-checked exactly like `Envelope.data` (never accepts a non-serializable value).
  - `to_json_dict()` renders the schema shape: `id`/`intent_id` as nested `{"writer_id", "counter"}` objects (the composite stays structured, never string-encoded — no parser to write or maintain), `phase`/`story` as their string forms, optional keys (`story`, `intent_id`) omitted entirely when absent (mirrors `Finding.to_json_dict`'s own optional-`path` convention).
- **Timestamp pattern is stricter than `core/egress.py::_TIMESTAMP_PATTERN`, deliberately**: `^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{3}Z$` — exactly 3 fractional digits, `T` and `Z` only (no space form, no `+00:00` form). A private constant in `core/journal.py`, NOT imported from `core/egress.py` (that pattern is module-private and answers a different, looser question — see Design Notes).
- `SIDECAR_THRESHOLD_BYTES = 4096`. `prepare_for_write(entry: JournalEntry) -> PreparedWrite` (pure): if `payload`'s own UTF-8 JSON byte length exceeds the threshold, returns a `PreparedWrite` whose `entry.payload` is replaced with `{"sidecar_ref": "blobs/<writer_id>-<counter>.json"}` (derived solely from `entry.id`, globally unique within the run by construction — no path input needed) plus the ORIGINAL payload's serialized text as `sidecar_content`; otherwise `sidecar_relative_path`/`sidecar_content` are `None`. `PreparedWrite.line` is the (possibly rewritten) entry's `to_json_dict()` serialized via `json.dumps(..., sort_keys=True)`, WITHOUT a trailing newline (the newline is the adapter's concern).
- `ports/fs.py::FsPort` gains two methods, implemented on `LocalFs`:
  - `append_line(path: Path, line: str, *, fsync: bool) -> None` — AD-30's protocol verbatim: one `os.write()` of `(line + "\n").encode("utf-8")` on a descriptor opened `os.O_WRONLY | os.O_APPEND | os.O_CREAT` (mode `0o666`, matching `_tmp_sibling`'s existing mode), `os.fsync`ed only when `fsync=True`, then closed — no `open()`/`fdopen()` buffered stream. Does **not** create parent directories (unlike `write_text_atomic`): the run directory's existence is itself a meaningful precondition (see `create_dir_exclusive` below), so a missing parent is a real `FsError`, not an auto-create.
  - `create_dir_exclusive(path: Path) -> None` — a bare `path.mkdir()` (no `parents=True`, no `exist_ok`). Raises the new `DirectoryAlreadyExistsError(FsError)` (a distinguishable subtype, not a generic `FsError`) when `path` already exists; any other `OSError` still raises plain `FsError`. Mirrors AD-25's "`mkdir`, not `O_EXCL`" correction verbatim — directories are already exclusive via `mkdir(2)`'s own `EEXIST`.
- Unit-test every new pure function/dataclass invariant in `core/journal.py` against `tests/unit/test_journal.py` (mirrors `test_identity.py`/`test_egress.py` conventions), the two new `LocalFs` methods in `tests/unit/test_fs_local.py`, and `schemas/journal.json` via `jsonschema.validate` against representative built entries (mirrors `test_egress.py`'s `_schema()`/`jsonschema.validate` pattern for `gate-record.json`).
- **The concurrency test** (this story's headline AC) lives in `tests/unit/test_fs_local.py` and tests `append_line` directly (not through `core/journal.py` — it proves the adapter's OWN physical guarantee, independent of entry-shaping): one long-lived `threading.Thread` appending many lines in a loop, alongside several short-lived threads each appending a handful of lines then exiting, all targeting the SAME file concurrently, each thread using its own `writer_id` and a locally-owned monotonic counter (no lock — AD-28 requires none). After joining every thread, read the file back and assert every line parses as JSON (zero malformed lines) and the set of `(writer_id, counter)` pairs across all lines has zero duplicates and its size equals the total append count.
- `tests/meta/test_ad11_write_boundary.py`'s `_RecordingFs` fake gains `append_line`/`create_dir_exclusive` (mirrors Story 1.5's identical precedent of extending this fake whenever `FsPort` grows) so the AD-11 write-boundary guard keeps covering every method.

**Block If:** none — every decision here either follows an explicit architecture rule (AD-25/AD-28/AD-30) or reuses an existing precedent in this codebase (slug validation, timestamp double-validation, dataclass-invariant-at-construction, "pure core + adapter physical write" split); no product ambiguity requires a human decision.

**Never:**
- Do not wire any CLI command (no `marshal run`/`marshal launch` exists anywhere in the codebase — confirmed live, `find src -iname '*journal*'` returned nothing before this story). Nothing calls `mint_run_id`/`create_dir_exclusive`/`append_line` end-to-end yet; that's Story 3.3 (`Detached launch with scoped story selection`, `backlog`).
- Do not implement the `sessions/` namespace, session-id minting, or the "a session-namespace record binds to a `run_id` when supplied" rule (AD-25's own amendment). No session concept exists anywhere in this codebase today (`cli/gate.py`'s `--run` stub is the only related surface, and it stays untouched — see below); inventing session-id minting with no real caller would be exactly the kind of unattended surface-widening this project's own precedent (Stories 2.4/2.5/2.6) explicitly avoids. Log as follow-up.
- Do not touch `cli/gate.py`'s existing `--run`/`MRS-GATE-005` stub, `core/gate.py`, or any registered `MRS-*` finding code — this story has no real caller to attribute a `Finding` to (mirrors Story 2.6's identical "pure mechanism, zero new registered codes" precedent: `DirectoryAlreadyExistsError`/malformed-input `ValueError`s stay Python exceptions, not `Finding`s, until a real CLI-wiring story classifies them).
- Do not implement `core/journal.py`'s READ side (the fold, quarantine-on-malformed-line, `unevaluable` scoping) — that is Story 3.2's own title and AC set, `backlog`. This story proves the WRITE protocol is correct under concurrency; it does not read a journal back except inside its own tests.
- Do not decide the concrete on-disk root (`runs/` vs `sessions/`, under which Tier-3 subpath) — no caller exists yet to need it; `create_dir_exclusive`/`append_line` take a caller-supplied `Path`, agnostic to where it lives.
- Do not close the existing `deferred-work.md` entry recording that `core/journal.py` must eventually record `{marshal_version, harness_version}` per run (FR-57, logged at Story 1.9) — `payload: Mapping[str, object]` is already generic enough to carry those fields once a real caller exists, but no caller does yet in this story, so the entry stays open, updated to note the writer now exists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid run id | `mint_run_id("pyforge-marshal", "20260803T054512123Z", "a1b2c3")` | `"pyforge-marshal-20260803T054512123Z-a1b2c3"` | No error expected |
| Malformed slug | `mint_run_id("Not_Valid!", ...)` | — | `ValueError` naming the slug |
| Outcome entry, no intent_id | `build_entry(phase=OUTCOME, intent_id=None, ...)` | — | `ValueError`: outcome requires intent_id |
| Observation entry with intent_id | `build_entry(phase=OBSERVATION, intent_id=some_id, ...)` | — | `ValueError`: observation forbids intent_id |
| Small payload | `payload={"a": 1}` | `prepare_for_write` returns `sidecar_relative_path is None`, `line` embeds the payload inline | No error expected |
| Oversized payload (>4 KiB) | `payload` serializing to 5000 bytes | `prepare_for_write` returns `payload={"sidecar_ref": "blobs/<writer_id>-<counter>.json"}` in `line`; `sidecar_content` carries the original 5000-byte JSON | No error expected |
| Non-serializable payload | `payload={"x": object()}` | — | `ValueError` (mirrors `Envelope.data`'s own check) |
| Concurrent append, real files | 1 long-lived + N short-lived threads, same path | Every appended line is valid JSON; `(writer_id, counter)` pairs are pairwise distinct | No error expected — the AC's own headline case |
| Run directory collision | `create_dir_exclusive(path)` where `path` already exists | — | `DirectoryAlreadyExistsError` (`FsError` subtype); directory left untouched |
| Fresh run directory | `create_dir_exclusive(path)` where `path` is absent | Directory created | No error expected |
| append_line, missing parent | `path`'s parent directory does not exist | — | `FsError` (no auto-mkdir, unlike `write_text_atomic`) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py` -- NEW. `Phase`, `JournalEntryId`, `JournalEntry`, `build_entry`, `PreparedWrite`, `prepare_for_write`, `mint_run_id`, the millisecond timestamp pattern. Pure (AD-4).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/fs.py` -- EDIT. Add `append_line`/`create_dir_exclusive` to the `FsPort` Protocol, following the file's existing per-story docstring-narrative convention.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/fs_local.py` -- EDIT. Implement both on `LocalFs`; add `DirectoryAlreadyExistsError(FsError)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/journal.json` -- NEW. One journal line's shape, `additionalProperties: false`, mirroring `gate-record.json`'s closed-schema discipline; nested `id`/`intent_id` sub-schemas; `phase` enum; conditional `intent_id` requirement expressed via `if`/`then` (mirrors `gate-record.json`'s `commandReport` `allOf`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_journal.py` -- NEW. Every `core/journal.py` invariant + the I/O matrix + `jsonschema.validate` round-trips against `schemas/journal.json`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_fs_local.py` -- EDIT. `append_line`/`create_dir_exclusive` unit coverage, plus the concurrency test.
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad11_write_boundary.py` -- EDIT. `_RecordingFs` gains the two new methods; write-boundary assertions extended.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- EDIT. Update the existing Story-1.9-logged entry (`core/journal.py` now exists but has no caller yet) and add follow-ups for: the `sessions/` namespace + session-id minting, and CLI wiring (Story 3.3).

## Tasks & Acceptance

**Execution:**
- [x] `core/journal.py` -- add `Phase`, `JournalEntryId`, `JournalEntry`/`build_entry`, `mint_run_id`, `PreparedWrite`/`prepare_for_write`, the millisecond timestamp pattern -- the pure entry-shaping and id-minting core the AC requires.
- [x] `ports/fs.py` -- add `append_line`/`create_dir_exclusive` to `FsPort`.
- [x] `adapters/fs_local.py` -- implement both per AD-30/AD-25's physical protocols; add `DirectoryAlreadyExistsError`.
- [x] `schemas/journal.json` -- author the closed schema for one journal line.
- [x] `tests/unit/test_journal.py` -- new file, full coverage of the pure core module + schema round-trips.
- [x] `tests/unit/test_fs_local.py` -- extend with `append_line`/`create_dir_exclusive` coverage + the concurrency test (this story's headline AC).
- [x] `tests/meta/test_ad11_write_boundary.py` -- extend `_RecordingFs`.
- [x] `deferred-work.md` -- update the Story-1.9 entry; log the two follow-ups above.

**Acceptance Criteria:**
*(Story 3.1's ACs from `epics.md`, preserved as the contract of record; parenthetical notes mark what this story satisfies vs. defers.)*
- Given any run or session invocation, when the identifier is minted, then Marshal mints it at `intent` time, before any spawn — globally unique, `<slug>-<utc-compact>-<random>`, sortable chronologically within a slug but not across the fleet; fleet-wide chronology sorts on `ts`, never on the id (satisfied for RUN ids via `mint_run_id`; session-namespace minting deferred — no session concept exists yet, see Never)
- And the harness's own identifier is recorded as `harness_run_id` on the first `outcome` entry and is never a key, a path segment, or a grouping field (`JournalEntry.payload: Mapping` is generic enough to carry `harness_run_id`; no real caller writes one yet — deferred to the launch story that first spawns a harness process)
- And run directories are created with `mkdir`, which already fails `EEXIST`; a collision is a hard finding, never an append (`create_dir_exclusive` raises `DirectoryAlreadyExistsError`; classifying it as a registered `Finding` is deferred to the CLI-wiring story per Never, since no caller exists yet to attribute one to)
- And non-run invocations (standalone gate evaluation, adapter probe) mint into a separate `sessions/` namespace excluded from fleet folds by construction, not by filtering (deferred — see Never; no session concept exists anywhere in this codebase)
- And every entry carries `{id, ts, run_id, story?, kind, phase, intent_id?, payload}` where `id` is the composite `(writer_id, counter)` — monotonic within a writer, never across the run — and `phase ∈ intent | outcome | observation`, with `intent_id` mandatory on every `outcome` and absent on every `observation` (satisfied: `JournalEntry.__post_init__`)
- And each append is a single `os.write()` of one complete newline-terminated line on an `O_APPEND|O_CREAT` descriptor, `fsync`ed for `phase: intent`, with no buffered stream held open across appends (satisfied: `LocalFs.append_line`; the `fsync`-for-`intent` DECISION is the caller's — `append_line` takes an explicit `fsync` flag rather than inspecting a phase string, keeping the adapter domain-agnostic, matching every other `FsPort` method's own generic-primitive convention)
- And payloads over 4 KiB go to a sidecar blob with a reference in the entry (satisfied: `prepare_for_write`)
- And timestamps carry millisecond precision and total order is `(ts, writer_id, counter)` — a total order without cross-writer coordination, explicitly not a causal order; no consumer may infer causality from adjacency (satisfied: the millisecond timestamp pattern + `JournalEntryId`'s `order=True` tail; the "no consumer may infer causality" clause is a fold-side/consumer-side discipline, out of this writer-only story's scope)
- And a concurrency test with a long-lived writer and repeated short-lived writers produces zero malformed lines and zero duplicate `(writer_id, counter)` pairs — the malformed-line assertion alone tests atomicity, not identity, and would pass while the id invariant was violated (satisfied: `tests/unit/test_fs_local.py`'s new concurrency test asserts both properties independently)

## Spec Change Log

## Review Triage Log

### 2026-08-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 0, medium 3, low 4)
- defer: 5 (high 0, medium 0, low 5)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` `LocalFs.append_line` discarded `os.write()`'s return value; POSIX permits a short write even for a regular file, which would silently truncate the appended line. Fixed: the write's actual byte count is checked against the intended length and raised as a loud `FsError` (never silently retried -- a retry could let a different writer's complete line land in the gap between two partial writes of this call, which is worse than failing loudly). Added `test_append_line_raises_fs_error_on_a_short_write` (monkeypatches `os.write`).
  - `[medium]` `[patch]` `append_line` never rejected a `line` containing an embedded newline, even though the primitive's entire contract is "one physical line per call" -- an embedded `\n` would silently split into two physical lines with no error. Fixed: rejected up front with `FsError`. Added `test_append_line_rejects_a_line_with_an_embedded_newline`.
  - `[medium]` `[patch]` `JournalEntry.__post_init__` accepted a payload with non-`str` keys (e.g. `{1: "a"}`) at construction (plain `json.dumps` silently coerces them on output), but `prepare_for_write`'s later `json.dumps(..., sort_keys=True)` call crashes on the SAME payload with an unhandled `TypeError` (sorting mixed-type key/value tuples). Fixed: non-`str` payload keys are now rejected at construction with a clear `ValueError`, the one place every `JournalEntry` is built. Added `test_journal_entry_rejects_non_str_payload_key`.
  - `[low]` `[patch]` No test proved `os.fsync` was actually called when `fsync=True` and skipped when `fsync=False` -- every prior test only checked final file content, which would pass identically if the `if fsync: os.fsync(fd)` line were deleted or inverted. Added `test_append_line_calls_os_fsync_only_when_requested` (monkeypatches `os.fsync`).
  - `[low]` `[patch]` No test exercised an out-of-vocabulary `phase` value through `build_entry`. Added `test_build_entry_rejects_out_of_vocabulary_phase`.
  - `[low]` `[patch]` The concurrency test only exercised very short lines from a handful of threads -- nothing proved the same atomicity/identity guarantee holds for lines near the 4 KiB sidecar boundary, the largest a real inlined line is ever meant to get and the likeliest place for a short write to actually surface. Added `test_append_line_is_safe_under_concurrent_writers_near_the_sidecar_threshold` (6 writers x 20 lines each, ~3.9 KiB padded lines).
  - `[low]` `[patch]` `append_line`'s concurrency guarantee (`O_APPEND`'s atomicity) is a local-filesystem property, not a POSIX universal -- unreliable on some network filesystems (e.g. classic NFS) -- and this was undocumented anywhere an operator would see it. Added a caveat to `append_line`'s docstring in both `ports/fs.py` and `adapters/fs_local.py`.
  - `defer` (5): `prepare_for_write`'s 4 KiB threshold measures only `payload` bytes, not the full envelope+payload line (AD-30's "line exceeding 4 KiB" vs. this story's governing AC's "payloads over 4 KiB" -- the code follows the AC, the contract of record; the tension is between two planning artifacts, not this story's spec/implementation) -- logged. No check that an `outcome` entry's `intent_id` doesn't self-reference its own `id` -- logged, belongs to Story 3.2's fold where pairing is actually validated, not this story's writer. `JournalEntryId.writer_id` has no length bound despite becoming part of a sidecar blob filename -- logged, no real caller mints one yet to validate a bound against. `create_dir_exclusive` raises the identical `DirectoryAlreadyExistsError` for a real directory collision vs. a stray file occupying the path -- logged, a diagnostic-precision gap, not a safety gap (both cases correctly refuse to write). `append_line` wraps an `os.fsync` failure (after a successful `os.write`) into the same generic `FsError` as a write failure, so a future naive retry-on-`FsError` caller could duplicate an already-written line -- logged for whichever future story builds retry logic around this primitive.
  - `reject` (5): "`JournalEntryId`'s `order=True` sorts `writer_id` lexicographically, so `short-lived-10` sorts before `short-lived-2`" -- AD-28 requires only a deterministic tie-break, not a numerically-intuitive one; lexicographic string comparison satisfies the stated contract, and no consumer relies on numeric ordering of arbitrary writer-id text. "`mint_run_id`'s `utc_compact` is validated by regex only, never calendar-validated, inconsistent with `JournalEntry.ts`'s `datetime.fromisoformat` check" -- a deliberate, already-documented design choice (the module's own comment: `utc_compact` is an opaque, already-formatted sort key, mirroring `build_gate_record`'s established precedent of never validating a caller-supplied fact like `tree_revision` names a real commit). "`append_line`/`create_dir_exclusive` don't type-check their own `path`/`line` parameters the way `write_redacted_atomic` does" -- matches this SAME file's own general precedent (every other `FsPort` method except `write_redacted_atomic`, which has a documented cross-module type-boundary reason, trusts its typed parameters without a defensive `isinstance` check). "`JournalEntry` is `@dataclass(frozen=True)` (auto-`__hash__`) but stores `payload` as a plain `dict` (unhashable), so `hash(entry)` raises `TypeError` despite the frozen contract implying hashability" -- identical, already-shipped, already-reviewed precedent in `core/model.py::Envelope` (`data: dict`, also frozen) since Story 1.1; `JournalEntry`'s own docstring explicitly mirrors that convention, and nothing anywhere hashes a `JournalEntry`. "The `deepcopy` guard around `payload` only catches `TypeError`; a pathologically deep payload could raise `RecursionError` instead, bypassing the documented `ValueError` contract" -- identical pre-existing pattern in `core/model.py::Envelope.__post_init__`'s own `copy.deepcopy(self.data)` guard; fixing it (if warranted) is a cross-cutting change spanning both classes, out of this story's scope.

## Design Notes

**Why no CLI wiring, again.** This is the fourth consecutive Epic 1/2/3 story (after 2.4, 2.5, 2.6) to ship a fully-tested pure mechanism with zero real caller. It's not a pattern of convenience here — it's structural: `core/journal.py` is Story 3.1's OWN prerequisite for every later Epic-3 story (3.2's fold, 3.3's launch, 3.4's supervisor), so by definition nothing in the tree can call it yet. `deferred-work.md`'s existing Story-1.9 entry already anticipated this exact moment ("Story 3.1's journal writer must record `{marshal_version, harness_version}`... once it exists") — this story makes that entry's precondition true without yet satisfying its obligation, and the entry is updated (not closed) to say so.

**Why `id`/`intent_id` are nested objects, not a delimited string.** A string encoding (`"writer_id:counter"`) would need an escaping rule the moment a `writer_id` could contain a colon, plus a parser Story 3.2's fold would then also need. A structured `{"writer_id", "counter"}` object needs neither — `json` handles it natively, and the composite nature AD-28 describes is literal in the shape, not implied by a separator convention.

**Why the timestamp pattern diverges from `core/egress.py`'s.** `_TIMESTAMP_PATTERN` deliberately tolerates multiple legitimate ISO-8601 spellings (space vs `T`, `Z` vs `+00:00`, optional fractional digits) because `gate-record.json` records are never string-sorted against each other. Journal entries ARE — AD-28's total order is `(ts, writer_id, counter)`, computed by comparing `ts` AS TEXT. Two spellings of the same instant would sort inconsistently relative to a canonically-spelled peer, silently violating the total order the fold (Story 3.2) depends on. One canonical spelling, enforced at write time, closes that gap before it can open.

**Why `append_line` takes an explicit `fsync` flag instead of a `phase` argument.** Every existing `FsPort` method is a dumb, domain-agnostic physical primitive (`write_text_atomic` doesn't know what content means; `copy_file` doesn't know it's copying an adapter config). Teaching `append_line` about `phase: intent` would be the one exception, and it isn't needed: the caller (a future orchestration layer) already knows the phase it's about to write, so it computes `fsync=(phase is Phase.INTENT)` itself and passes the bool. `core/journal.py::Phase` stays the one place that vocabulary lives.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all tests green, including the new `test_journal.py` and the extended `test_fs_local.py`/`test_ad11_write_boundary.py`, zero regressions.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, or only the same pre-existing unrelated failures already logged in `deferred-work.md`.

**Manual checks (if no CLI):**
- None -- no CLI surface is added by this story (see Never); all behavior is exercised by the automated suite above.

## Auto Run Result

Status: `done`.

**Summary.** Shipped Marshal's run-identity minting and journal-writer primitives (Story 3.1, architecture spine AD-25/AD-28/AD-30): `core/journal.py` (`mint_run_id`; `Phase`, the AD-28 three-valued vocabulary; `JournalEntryId`, the composite `(writer_id, counter)` id; `JournalEntry`/`build_entry`, with the outcome-mandatory/intent-and-observation-absent `intent_id` invariant enforced at construction; `PreparedWrite`/`prepare_for_write`, the 4 KiB sidecar-blob decision) plus two new `FsPort`/`LocalFs` primitives (`append_line`, AD-30's single-`os.write()`/conditional-`fsync` protocol; `create_dir_exclusive`, AD-25's exclusive-`mkdir` collision rule) and `schemas/journal.json`, the closed wire-shape schema. Every clock reading, random token, and writer id is caller-supplied (AD-4 purity, verified by the real `lint-imports` contract). No CLI wiring, no `sessions/` namespace, and no fold/read-side landed -- all explicitly out of this story's scope per its own Never clause, since no real caller (Story 3.3) or session concept exists anywhere in the codebase yet.

**Files changed:**
- `src/pyforge/marshal/core/journal.py` -- new. Pure entry-shaping/id-minting core.
- `src/pyforge/marshal/schemas/journal.json` -- new. Closed schema for one journal line.
- `src/pyforge/marshal/ports/fs.py` -- added `append_line`/`create_dir_exclusive` to `FsPort`.
- `src/pyforge/marshal/adapters/fs_local.py` -- implemented both on `LocalFs`; added `DirectoryAlreadyExistsError(FsError)`.
- `tests/unit/test_journal.py` -- new. Full coverage of `core/journal.py` + `jsonschema.validate` round-trips.
- `tests/unit/test_fs_local.py` -- extended: `append_line`/`create_dir_exclusive` coverage, two concurrency tests (short lines; near-4-KiB padded lines), fsync-call verification, short-write and embedded-newline rejection (review-pass additions).
- `tests/meta/test_ad11_write_boundary.py` -- extended `_RecordingFs` with both new methods.
- `_bmad-output/implementation-artifacts/deferred-work.md` (gitignored) -- updated the Story-1.9 `{marshal_version, harness_version}` entry (writer now exists, still uncalled); logged 2 CLI-wiring/session-namespace follow-ups during implementation + 5 more from the review pass (sidecar-threshold-vs-AD-30-wording tension, `intent_id` self-reference, `writer_id` length bound, dir-vs-file collision diagnostics, fsync-failure/retry-duplication hazard).

**Review findings breakdown:** Blind Hunter (adversarial) and Edge Case Hunter ran independently, blind to each other. 14 + 8 raw findings, deduplicated to 17 distinct: 7 patched (3 medium -- a short write silently truncating a line, an embedded newline splitting one physical line into two, a non-str payload key passing construction then crashing `prepare_for_write` two functions later; 4 low -- missing fsync-call test coverage, missing out-of-vocabulary-phase test, missing near-4-KiB-line concurrency coverage, an undocumented NFS/`O_APPEND` atomicity caveat), 5 deferred to `deferred-work.md` with evidence, 5 rejected as either matching this codebase's own already-shipped precedent (`Envelope`'s identical frozen-dataclass-with-a-dict-field and bare-`TypeError`-catch-around-`deepcopy` patterns; `write_redacted_atomic`'s own-parameter-type-checking exception, not the rule) or a deliberate, already-documented design choice (`utc_compact`'s opaque-sort-key treatment) or a non-issue against the actual stated contract (`writer_id`'s lexicographic-not-numeric sort order still satisfies AD-28's "deterministic tie-break"). No `intent_gap`, no `bad_spec` loopback -- zero re-derivation cycles.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **1231 passed, 8 deselected** (was 1225 after implementation, +6 from the review-pass patches), zero regressions. Independently re-run after every patch, not just trusted from the implementing subagent's report.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- **2 kept, 0 broken** (AD-3, AD-4), confirmed both before and after the review-pass patches.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- **58 passed, 2 failed**, confirmed identical to the pre-existing, already-logged `pyforge-steward`/`age` dependency-declaration gap (unrelated -- this diff touches only `pyforge-marshal`'s own files).
- Diff independently re-read file-by-file against the spec's Code Map and Never clause before committing; confirmed no file outside the sanctioned list was touched, and the implementing subagent's self-report was verified rather than trusted (read every new/changed file in full).

**Residual risks:**
- No CLI ever calls any of this story's primitives yet -- `mint_run_id`/`create_dir_exclusive`/`append_line` are fully tested but end-to-end unproven until Story 3.3 wires a real launch command.
- The 5 deferred findings (sidecar-threshold wording tension, `intent_id` self-reference, `writer_id` length bound, dir-vs-file collision diagnostics, fsync-failure/retry-duplication hazard) remain open in `deferred-work.md`; none block this story, but Story 3.2 (the fold) and Story 3.3 (the launch/retry caller) should read them before building on top of these primitives.
- The journal's READ side (fold, quarantine-on-malformed-line, `unevaluable` scoping) is entirely unbuilt -- Story 3.2's own scope, a hard prerequisite for `cli/gate.py`'s existing `--run`/`MRS-GATE-005` stub to ever produce a real answer.
