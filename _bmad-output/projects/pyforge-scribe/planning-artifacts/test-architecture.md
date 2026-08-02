---
title: "Test Architecture — pyforge-scribe"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "2 epics, 9 stories; unit-level pytest only — no integration/E2E tier exists yet"
target_coverage: "Unit coverage for every shipped module; no target set for unbuilt Epic 2 code"
---

# Test Architecture — PyForge Scribe

## Executive Summary

Authored 2026-08-02 to replace a fabricated placeholder (a 78-line generic
template with "Target Stories: TBD" on every row) discovered this session in
a bulk commit that also carried a false migration note and other fabricated
content — all found and remediated. Scribe is the smallest station in the
PyForge Guild fleet: 2 of 9 tracked stories marked `done`, one more (1.3)
**implemented and passing in code but not yet reflected in any status
ledger** (finding below), and 6 stories (1.4, 1.5, all of Epic 2) not started.
This document is short because Scribe's real footprint is short — padding it
with invented rows would be exactly the kind of fabrication it replaces.

**Real test suite today**: 3 files, **47 tests**, 943 lines, 100% unit-level,
all passing:

```
pixi run -e pyforge-scribe pyforge-scribe-test   # pytest src/shared/packages/pyforge-scribe/tests -q
...............................................  [100%]
47 passed in 0.74s
```

There is no integration, E2E, or meta tier yet — there is no multi-module
orchestration (graph compile, recall) to integration-test until Epic 2 ships.
`_bmad-output/projects/pyforge-scribe/tests/` (integration/e2e/meta/mocks/
performance subdirs, plus a `pytest.ini` and `conftest.py`) is unbuilt BMAD
scaffolding — the `conftest.py` literally says "Template — expand with
station-specific fixtures as stories are defined" and the `pytest.ini`
contains an unsubstituted `$(station)` template token. It is not wired to
the pixi task and collects nothing. The real suite lives at
`src/shared/packages/pyforge-scribe/tests/unit/`.

## Finding: Story 1.3 is code-complete but tracked as "backlog"

`src/pyforge/scribe/promote.py` (339 lines) and its test file
`tests/unit/test_promote.py` (457 lines, 23 tests) exist on `main` today and
implement Story 1.3's three acceptance criteria in full: `--promote` scans
and classifies user-local entries, halts before any write pending
`typer.confirm()`, and `rewrite_team_voice()` mechanically strips
first-person/"user prefers" framing and hash parentheticals while leaving
paths, commands, and labels untouched. `cli.py` wires `--promote` into the
`capture` command (`_run_promote`).

This code was lost and recovered: PR #168 (`d68187f4b3`, merged 2026-07-31)
cherry-picked it out of a **dangling commit** (`91d3571f10`) after a
bmad-loop dev-session timeout on the 1-3 worktree reset the branch back to
baseline, discarding the commit from reachable history — a follow-on Story
1.4 session found the trace (a stray `.pyc`), traced it via
`git log --all -- '*promote.py'`, and escalated with the SHA. The recovery
raised the suite from 18 to 47 tests. Full account:
`_bmad-output/projects/pyforge-scribe/implementation-artifacts/bmad-dev-auto-result-1-4-pointer-stub-write-back-idempotent-re-invocation.md`.

**None of the three status ledgers were reconciled after the recovery** —
`implementation-artifacts/sprint-status.yaml`,
`planning-artifacts/sprint-status.yaml`, and the dashboard-authoritative
`planning-artifacts/sprint-status-ledger.yaml` all still read
`1-3-promotion-workflow-proposal-then-confirm-team-voice-rewrite: backlog`.
This test-architecture document reflects the **real, verifiable code state**
(implemented, tested, merged) rather than the stale ledger value; reconciling
the ledgers themselves is outside this document's scope and is called out
separately in the report back to the requester.

## Test Strategy — Epic 1: Team Memory (Capture & Promotion)

| Story | Ledger status | Code status | Test file(s) | Level |
|-------|---------------|-------------|---------------|-------|
| **1.1** Package scaffold + direct capture | done | done | `tests/unit/test_capture.py` (11 tests) + 5 capture-only tests in `tests/unit/test_cli.py` | unit |
| **1.2** `CLAUDE.md` wiring | done | done | none — the AC specifies manual verification ("ask Claude to list every entry currently in team memory"); no pytest surface exists for a markdown import line | manual |
| **1.3** Promotion workflow | backlog *(drift — see Finding above)* | implemented | `tests/unit/test_promote.py` (23 tests: 12 classification, 7 team-voice rewrite, 3 `apply_promotion`, 1 `default_user_local_root`) + 6 promote-flow tests in `test_cli.py` | unit |
| **1.4** Pointer-stub write-back + idempotent re-invocation | backlog | not started | none — `promote.py`'s own docstring reserves this scope explicitly ("Pointer-stub write-back... is Story 1.4 — out of scope here"); `test_apply_promotion_writes_via_capture_and_source_is_untouched` asserts today's (pre-1.4) behavior, that the source file stays byte-for-byte unchanged | **planned:** unit tests on the pointer-stub rewrite (`promoted: true` + redirect body) and a re-invocation test asserting a second `--promote` run classifies the stub `already-promoted` and skips it (FR-5/FR-6) |
| **1.5** Seed promotion — end-to-end proof | backlog | not started | none | **planned: not a pytest file.** The AC requires the promotion be "performed by the tool, not authored by hand" against the two real `feedback_bmad_uses_cfe_skill.md` / `feedback_bmad_runs_cfe_retro.md` entries — the proof artifact is the resulting git diff from a real `scribe capture --promote` invocation, verified by inspection, once 1.3+1.4 are both reconciled/complete |

## Test Strategy — Epic 2: Knowledge Graph (Compile & Recall)

Zero implementation exists. `cli.py` ships two intentional stub subcommands
(`graph compile`, `recall`) that print `"not yet implemented"` and touch no
filesystem — covered by `test_graph_compile_stub_touches_nothing_and_exits_0`
and `test_recall_stub_touches_nothing_and_exits_0` in `test_cli.py`. These
two tests prove **CLI contract stability** (FR-14 — the top-level command
shape doesn't change between epics), not Epic 2 functionality; they are
scoped to Story 1.1's scaffold, not to any Epic 2 story.

| Story | Code status | Planned test level (once built) |
|-------|-------------|----------------------------------|
| **2.1** `GraphStore` port + flat-file v1 adapter | not started | Unit: protocol contract + concrete adapter round-trip. The AC additionally mandates a dedicated **offline/air-gap conformance test** (AD-6, "matching this repo's `deckcraft` precedent") as part of this story's own deliverable, not deferred. |
| **2.2** Nightly compile from named tool surfaces | not started | Integration: compile against fixture surfaces (`.claude/memory/`, a `.memlog.md`, git history) + an idempotency test (re-run with no new activity produces zero diff, FR-11). |
| **2.3** Fact supersession in the compiled graph | not started | Unit: a superseding capture ends the prior node's validity without deleting it; a query still resolves the superseded record (FR-10). |
| **2.4** `scribe recall` — grounded, cited answers | not started | Unit/CLI: a grounded query returns a resolvable citation (FR-12, AD-8 — no answer without one); an ungrounded query returns explicit "no grounded answer found"; a same-query/two-invocation test for FR-13's shared-graph consistency. Extends the existing stub test rather than replacing it. |

## Coverage Summary

| Level | Stories covered | Status |
|-------|------------------|--------|
| **Unit** | 1.1, 1.3 (2 of 9 tracked; 3 of 9 by real code state) | shipped, 47/47 passing |
| **Manual** | 1.2 | shipped, no automated surface (by design — CLAUDE.md import) |
| **Integration / E2E / Meta** | none | no tier exists; nothing to integrate until Epic 2 ships |
| **Planned, unbuilt** | 1.4, 1.5, 2.1–2.4 | test levels noted per-story above; no files exist, none are invented here |

## Framework & Tooling

**Pytest** only, run via the pixi task defined in root `pixi.toml`:
`[feature.pyforge-scribe.tasks.pyforge-scribe-test]` →
`pytest src/shared/packages/pyforge-scribe/tests -q`. No `pytest.ini` is
needed or present in the package itself; the stray one under
`_bmad-output/projects/pyforge-scribe/` (noted above) is inert scaffolding.

CLI tests use Typer's `CliRunner`; every filesystem-touching test
`monkeypatch.chdir()`s into `tmp_path` and never touches the real repo
`.claude/memory/` tree. `capture.py`'s concurrent-write lock is exercised
directly with a `ThreadPoolExecutor` in `test_concurrent_captures_lose_no_entries`
— no mock is needed since the lock is a real `fcntl`/`msvcrt` advisory lock
on a tmp-dir-scoped file.

## Readiness Checklist

- [x] All 9 stories enumerated from `epics.md`
- [x] Shipped stories mapped to real, existing test files (1.1, 1.3)
- [x] Manual-verification story documented as such, not fabricated a test for (1.2)
- [x] Unbuilt stories (1.4, 1.5, 2.1–2.4) given planned test levels only — no invented filenames
- [x] Status-ledger drift on Story 1.3 identified and evidenced (PR #168)
- [ ] Integration tier scaffolded (nothing to integrate yet)
- [ ] E2E tier scaffolded (no CLI-to-graph round trip exists yet)
- [ ] Sprint-status ledgers reconciled to Story 1.3's real code state (tracked separately, not this document)

---

**Status**: DRAFT — accurate as of 2026-08-02; re-verify against `git log` /
the pixi test task before trusting story-status cells past this date.

**Last updated**: 2026-08-02
