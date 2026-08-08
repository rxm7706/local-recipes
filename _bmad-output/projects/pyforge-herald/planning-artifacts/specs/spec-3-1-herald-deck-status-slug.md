---
title: 'herald deck status [<slug>]'
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

**Problem:** Epics 1 and 2 built `seed` (repo -> Design) and `pull` (Design -> repo), but an
operator has no way to see a deck's bridge state without running a pull and inspecting its result.
With multiple decks seeded (`pyforge-marshal`, `pyforge-herald`, `pyforge-mason`, `pyforge-doctor`,
and growing), there is no single command reporting which decks are linked, which have Design-side
edits waiting to be pulled, and which last-pull timestamps are on record.

**Approach:** Implement `deck_pipeline.status` (CAP-3): a read-only report over every known deck (or
one, given a slug), each with a fresh `read_file(if_none_match: <recorded etag>)` comparison per
tracked artifact against Design -- never a body pull, only the etag short-circuit. Wire it to
`herald deck status [<slug>]` via `cli.py`'s third `dispatch`-routed subcommand, printing one JSON
array (FR-11's machine-readable requirement). This story also lands a genuine spine amendment: the
`DesignTransport` port gains a 9th method, `list_files`, per Story 1.2's own review finding F10
("route it as a spine decision ... before Epic 3 / Story 1.6 -- not as an adapter-local addition").
Story 3.2 (this same PR/session) is the reason `list_files` had to land now rather than later --
FR-12's stale-hand-mirror heuristic cannot be implemented at all without it -- but the port change
itself, and `status`'s own etag-comparison logic, belong to this story.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.status(transport, *, slug=None, repo_root, state_path=None) -> list[DeckStatus]`.
  With no `slug`: reports every deck `status` can discover -- the union of every slug already in
  `state.py` (a new `state.known_slugs(state_path)` read-only helper) and every
  `presentations/<slug>/` directory carrying a `README.md` (a deck that exists locally but was never
  seeded) -- so an unseeded deck is reported `linked: false` rather than silently omitted (matches
  the AC's "some seeded, some not" scenario). With a `slug`: reports only that one, even when it is
  entirely unknown (no state entry, no local directory) -- returns a single unlinked `DeckStatus`
  rather than raising, unlike `pull_*`'s "must have been seeded" refusal; status reporting on an
  unseeded deck is itself a normal, informative answer.
- Per linked deck: for every artifact key already recorded in its `state.py` `etags`, resolve the
  Design-side path (`_remote_path_for_artifact`, generalizing the same per-artifact naming convention
  `pull_prototype`/`pull_marp_source`/`pull_standalone_bundle` each already derive for their own
  single artifact) and call `transport.read_file(if_none_match: <recorded etag>)`. Classifies:
  `"unchanged"` when every comparison came back `{unchanged: true}` (or there are no tracked
  artifacts yet -- seeded but never pulled); `"changed"` when at least one comparison reported a real
  change and every comparison could be made; `"conflict"` when at least one comparison itself raised
  a `TransportError` (unreachable, or the tracked file is gone server-side) -- conflict takes
  precedence over changed, since an operator cannot safely decide "pull" is the right move without
  first resolving the failed comparison.
- Zero writes on either surface (FR-13, NFR-08): `status` calls only `state.read` (never
  `state.write`) and only `transport.read_file`/`transport.list_files` (never any write-side
  transport method). Verified in tests two ways: a `FakeStatusTransport` whose every write-side
  method raises `NotImplementedError`, and a byte-identical `.herald/bridge-state.json` before/after.
- `DesignTransport` (the port, `transport/base.py`) gains `list_files(*, project_id) -> Sequence[ListedFile]`
  as its 9th method, implemented identically (thin `_call_json("list_files", ...)` wrapper, same
  marshalling discipline as every other method) in both `McpTransport` and `AgentSdkTransport`. A new
  `ListedFile` dataclass (`path`, `etag`, `size: int | None`) is the port's return shape.
- `cli.py`'s `deck status [<slug>]` subparser: `slug` is `nargs="?"` (optional, unlike
  `seed`/`pull`'s required positional) plus `--repo-root`. Routed through `dispatch` (AD-6), mirroring
  `_run_deck_seed`/`_run_deck_pull`'s composition shape exactly (`McpTransport()` built inside
  `operation`, never before `dispatch`). Always prints one JSON array to stdout -- there is no
  separate human-prose success line, unlike `seed`/`pull`.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No `--json`/plain-text toggle -- `deck status` output is always JSON (unlike the Epic 6 Moment
  subcommands' `--json` flag), since FR-11 requires machine-readable output unconditionally.
- No write-side call anywhere in `status`'s own code path -- this is the story's central guarantee;
  see the zero-write bullet above.
- No change to `pull_prototype`/`pull_marp_source`/`pull_standalone_bundle`'s own behavior -- `status`
  reuses their per-artifact naming *convention* (generalized into `_remote_path_for_artifact`) but
  does not alter their code.
- No live MCP call anywhere in this package's own test suite -- every test injects a hand-written
  fake `DesignTransport`; the `deny_network` autouse fixture is the backstop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No slug, mixed deck set | some decks seeded, some only local dirs | one `DeckStatus` per known deck, `linked` true/false accordingly | No error |
| Slug given, linked | `state.py` has an entry | single-element list, that deck only | No error |
| Slug given, unknown | no state entry, no local dir | single unlinked `DeckStatus`; no transport call | No error |
| All tracked artifacts unchanged | every `read_file` answers `{unchanged: true}` | `sync: "unchanged"` | No error |
| Never pulled | `etags == {}` | `sync: "unchanged"`; no `read_file` call at all | No error |
| One artifact changed | one `read_file` reports a real change | `sync: "changed"` | No error |
| One comparison fails | `read_file` raises `TransportError` for one artifact | `sync: "conflict"` even if another artifact is merely changed | No error (caught internally) |
| Unrecognized tracked artifact key | a hand-edited/future-schema `etags` key | refused before any further comparison | `HeraldError` naming the key |
| CLI, no slug | `herald deck status` | exit 0; one JSON array on stdout | No error |
| CLI, with slug | `herald deck status <slug>` | exit 0; one-element JSON array | No error |
| CLI `HeraldError` | `deck_pipeline.status` raises | one stderr line; exit per `errors.exit_code_for` | per error type |
| `herald deck status --help` | argparse | help text | exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` -- edit -- new
  `ListedFile` dataclass, `list_files` added to the `DesignTransport` Protocol (9th method), module
  docstring records the F10 spine-amendment rationale.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py` -- edit --
  `McpTransport.list_files`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/agent_sdk_transport.py` -- edit --
  `AgentSdkTransport.list_files`, identical marshalling.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/__init__.py` -- edit -- re-exports
  `ListedFile`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/state.py` -- edit -- new `known_slugs`
  read-only helper.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- `DeckStatus`,
  `_remote_path_for_artifact`, `_status_for_slug`, `_known_slugs`, `status`. (`_is_stale_mirror` and
  the two threshold constants also land here, in this same edit -- see spec-3-2's own Intent for why
  they are documented as that story's own scope even though the code arrived in one commit.)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck status [<slug>]`
  subparser, `_run_deck_status`, `main` routes `deck_command == "status"`.
- `src/shared/packages/pyforge-herald/tests/test_transport_base.py`,
  `tests/test_mcp_transport.py`, `tests/test_agent_sdk_transport.py`, `tests/test_bridge.py` -- edit
  -- `list_files` marshalling coverage; the "exactly N port methods" test widened 8 -> 9; the
  hand-written `FakeTransport` doubles in `test_bridge.py` gain `list_files`.
- `src/shared/packages/pyforge-herald/tests/test_deck_status.py` -- create -- `FakeStatusTransport`
  (read-only double), the I/O matrix's `status` rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_status.py` -- create -- the I/O matrix's CLI
  rows; `deck_pipeline.status` monkeypatched so only the CLI's own composition is under test.

## Design Notes

**Why `list_files` had to land in this story, not later.** `DesignTransport` was fixed at exactly 8
tools by Story 1.2/AD-3, and Story 1.2's own review (finding F10) logged widening it as explicitly
out of scope for that story -- but named the exact future trigger: "FR-12 (stale hand-mirror
detection) needs to enumerate a Design project's files ... route it as a spine decision ... before
Epic 3." `read_file` cannot substitute: it requires already knowing a path, and a hand-mirrored repo
copy predates Herald entirely, so no local record (`state.py`'s tracked etags, the README registry)
ever names its files. `status` (this story) is the natural place for the amendment to land, since
`_is_stale_mirror` (Story 3.2) is `status`'s own last step per deck.

**Judgment call: `sync` is a plain `str | None`, not an enum.** The three values
(`"unchanged"`/`"changed"`/`"conflict"`) are a closed set today, but a `str` keeps the JSON output
(FR-11) trivial -- no enum-to-string translation layer -- and matches this codebase's existing
convention of plain-string status fields elsewhere (e.g. `PullResult` has no enum either).

**Judgment call: `conflict` beats `changed`, not the reverse.** A deck with two tracked artifacts,
one reporting a genuine change and one whose comparison itself failed, is reported `conflict`
wholesale rather than `changed`. Rationale: an operator seeing `"changed"` reasonably expects `pull`
to succeed; if a different artifact's comparison is actually broken (unreachable transport, or the
tracked file deleted server-side), presenting `"changed"` would be a false green light on a deck that
is not actually in a known-good state end to end.

**Judgment call: `known_slugs` is a small, focused addition to `state.py`, not a reach into its
private `_load_document`.** `deck_pipeline.py` needing "every slug currently recorded" is a genuine
new capability `state.py` did not previously expose (every existing caller wants exactly one slug).
Adding a one-line public function preserves `state.py`'s existing encapsulation discipline (every
other module reaches it only through `read`/`write`) rather than deck_pipeline.py importing a
leading-underscore name across the module boundary.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green (baseline 470 passed,
  2 skipped after Epic 2's close-out; **502 passed, 2 skipped** after this story + spec-3-2, +32 net
  new tests across both stories' shared commit set).
- `ruff format --check` / `ruff check` from the package root -- every file this story touches is
  clean (two pre-existing findings remain, both untouched by this story: `test_registry.py`'s import
  order, and an `SIM117` nested-`with` hit in `test_transport_base.py` at a line this story did not
  edit).
- `herald deck status --help` -- exit 0.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read after the suite was green, looking specifically for: the zero-write guarantee
actually holding (not merely asserted), the etag comparison using `if_none_match` correctly (not
accidentally forcing a full body pull), and `conflict` genuinely taking precedence over `changed`
when both occur in the same deck.

- `[none]` No defects found. Verified directly:
  - `test_status_never_writes_a_file_on_either_surface` asserts `.herald/bridge-state.json`'s bytes
    are byte-identical before/after a mixed-deck `status()` call, and that `FakeStatusTransport`
    (whose every write-side method raises `NotImplementedError`) was never called with anything but
    `read_file`/`list_files`.
  - `_status_for_slug`'s `read_file` call always passes `if_none_match=etag` -- the recorded etag,
    never `None` -- so a genuinely unchanged artifact always short-circuits per the existing
    `{unchanged: true}` wire contract `pull_prototype` already relies on; no new decode path was
    introduced.
  - `test_status_conflict_takes_precedence_over_changed` seeds two tracked artifacts, one answering a
    real change and one raising `TransportCallError`, and asserts the overall result is `"conflict"`.
- `addressed_findings`: 0. `followup_review_recommended: true` is set above per this repo's own
  practice of treating a same-agent self-review as insufficient on its own -- an independent second
  pass (and, per Story 2.1's own precedent, an eventual live-MCP smoke test of `list_files` and
  `status` against a real seeded deck) are the two checks this pass could not perform itself.
