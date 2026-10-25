---
title: 'pyforge-marshal — Retrospective (2026-10-25: marshal-mcp starts, the loop home stays clean, the PRD arrows trace)'
project: pyforge-marshal
date: '2026-10-25'
created: '2026-10-25'
updated: '2026-10-25'
scope: 'Story 103.1 changed pyforge-marshal/pyproject.toml (mcp>=2.2.0 for the official SDK server), which moves the chain''s code stage past the 2026-10-11 retro (the code→retro currency edge). This note covers Epics 103, 104 and 105: Story 103.1 (marshal-mcp on the official SDK, preflight proves it), Story 104.1 (the .mcp.json marshal renders never makes a loop home dirty) and Story 105.1 (every PRD FR arrow names the capability that realizes it), plus the frontier tier the 103.1 send-backs led to.'
evidence:
  - 'PR #2307 (Story 103.1, merged 67a4ae014c): six independent review rounds; dev passes on composer-2.5-fast (3) and Claude Fable 5.1 (1)'
  - 'PRs #2309, #2310, #2311: the opt-in fable tier on Cursor, its cost-catalog entry, then the frontier tier on the Claude Code harness'
  - 'Run pyforge-marshal-20261025T171322497Z-09a0b89c: verification refused (MRS-GATE-001, test_followup_review_carried); the verify-fix turn exited 1 on a Cursor usage limit (verify-fix.log) although the run resolved the claude profile'
  - 'PR #2307 head 10a7a2444a: every CI lane failed pixi install --locked ("lock file not up-to-date with the workspace") while a local pixi lock --dry-run --check passed'
  - 'PR #2312 (chain 104.1) and PR #2313 (Story 104.1, merged 21:56, 23 minutes after dispatch)'
  - 'PR #2314 (Story 105.1): 71 FR heading arrows re-mapped, review round 1 PASS with 13 operator-approved row amendments'
---

## What happened

- **marshal-mcp had never started.** `mcp/server.py` imported `FastMCP` from the third-party `fastmcp` package,
  which no pixi environment carries, and preflight only checked that the command resolved on `PATH`
  (`MRS-PREFLIGHT-012` stayed silent). Story 103.1 moved the server to the official SDK's `MCPServer`, gave it a real
  `--help` / `--version`, and made preflight run an `initialize` → `tools/list` handshake through a new
  `McpProbePort` / `adapters/mcp_stdio_probe.py` (spec `spec-103-1-…`).
- **The default tier could not finish 103.1.** Three composer-2.5-fast dev passes each failed independent review
  (rounds 2–5 in the spec's Review Triage Log). The blockers were process-control defects a green in-session review
  passed: no timeout on the read, `BrokenPipeError` escaping, only the direct child stopped, a drain that could hang,
  and an AC9 cheat sheet rendered at 80 columns. Two dev-pass records claimed "PASS" and "AC9 green" that a reviewer
  disproved; round 5 sent them back, and the next pass corrected the records and deleted the two team-memory notes
  that repeated them. The operator approved a stronger model
  ("can you use CLAUDE FABLE").
- **The first stronger tier never ran.** The `fable` tier on Cursor dropped its model override at launch
  (`MRS-DISP-043`: the model was not in `model_cost_catalog`, PR #2310 catalogued it), then Cursor refused the
  session on its monthly Fable usage limit. The operator ruled the `frontier` tier: the Claude Code harness with
  Claude Fable 5.1 (PR #2311). Its first launch needed the operator to renew the standalone `claude` CLI's OAuth
  session. The Fable pass fixed every round-5 blocker; round 6 passed with 0 blockers.
- **A run that did the work still refused to land.** The Fable pass set the spec `done` with
  `followup_review_recommended: true`, and `test_followup_review_carried` (a `pyforge-marshal-test` meta-test) reds a
  done-and-flagged spec with no deferred-work row, so verification refused (MRS-GATE-001). The verify-fix turn then
  launched on Cursor and exited 1 on Cursor's usage limit, although the run had resolved the `claude` profile. The
  flag cleared only when the independent round-6 review was recorded and `landing_review: passed` released the hold.
- **The help scrub missed two variables.** AC9's root cause was the cheat-sheet generator inheriting
  terminal-forcing variables (`FORCE_COLOR`, `GITHUB_ACTIONS`, …) from the harness. Round 6 found `PYTHON_COLORS`
  (Python 3.14 argparse colours its own `--help`, past `NO_COLOR`); the check of the round-6 fixes found
  `TYPER_USE_RICH`. Both are scrubbed now (`scripts/docs_station_cli.py::_TERMINAL_FORCING_VARS`).
- **A lock passed locally and failed every CI lane.** A dev-pass auto-checkpoint shortened the package `pixi.toml`'s
  `mcp = ">=2.2.0"` to `">=2.2"` without re-locking; `pyproject.toml` already said `mcp>=2.2`. A fresh pixi re-derives
  the source package's run-dependencies from `pyproject.toml` and compared `mcp >=2.2` with the lock's `mcp >=2.2.0`;
  the cached local pixi never re-derived it. A clean clone reproduced it (16 environments out of date on that one
  string); declaring `mcp>=2.2.0` fixed it. Team memory:
  `.claude/memory/feedback/a-cached-local-pixi-false-greens-a-lock-whose-path-dependenc.md`.
- **marshal's own file made its loop home dirty.** `marshal init` renders `.mcp.json` from
  `[mcp_servers.marshal]` (AD-43); nothing ignored it, so `marshal refresh` refused the `pyforge-marshal` home
  (`MRS-REFRESH-003`) and `bmad-loop run` would too. Story 104.1 added `/.mcp.json` to the seeded `model-ignores`
  region; it dispatched on the default tier and landed unheld in 23 minutes. After one `merge --ff-only` (134
  commits), `marshal refresh --project pyforge-marshal` reads the home clean and current.
- **The PRD's FR arrows were numbered, not traced.** The 2026-09-16 fold counted 71 FR heading arrows (`→ CAP-n`)
  in sequence; `fr-without-cap` checks only that a cited CAP exists, so nothing caught it. Story 105.1 re-mapped
  the 71 to the capabilities that realize them; review round 1 corrected 13 rows, which the operator approved.
  FR-144..FR-147 (§ 16.5) were the absorbed Spec's four scope items that the fold dropped; they wait on a
  source-capability decision (`DW-marshal-105-1`).

## What we changed

- 103.1 landed (#2307): the official-SDK server, the stdio handshake probe (deadline-bounded reads, concurrent
  stderr, one process-group stop on every path), `MRS-PREFLIGHT-012` with a redacted reason, and the AC8 mutation
  tests. Residual risks recorded in its Spec Change Log: a `setsid` descendant, the Windows stop path, `${VAR}`
  expansion.
- The `frontier` difficulty class (#2311): a story spec opts in with `difficulty: frontier`; the default tiers stay
  as they were.
- 104.1 landed (#2313); the marshal loop home is fast-forwarded and refreshes clean.
- 105.1 lands with this retro (#2314): 71 arrows traced, PRD § 44, `DW-marshal-105-1`.
- Operator practice held: a story whose earlier passes failed review dispatches with `landing_review: required`, and
  every send-back records its findings in the story spec before the next pass.

## Candidate fix stories (not minted here)

1. The verify-fix turn should resume on the harness profile the run resolved; on run
   `pyforge-marshal-20261025T171322497Z-09a0b89c` a `claude`-profile run's verify-fix turn launched `cursor-agent`.
2. A spec that a harness marks `done` with `followup_review_recommended: true` under `landing_review: required`
   should hold for the review rather than refuse verification on `test_followup_review_carried`.
3. When a path package's `pyproject.toml` or `pixi.toml` dependencies change, preflight could run
   `pixi install --locked` from a clean clone (or a fresh cache) for one environment, so a lock that only a cached
   pixi accepts is caught before push.
4. A dispatch auto-checkpoint that changes a manifest's dependency string should re-lock or refuse.
5. `fr-without-cap` could check that the cited CAP's own text names the FR (a trace check, not an existence check).
6. The cheat-sheet generator could build the `--help` child's environment from an allow-list rather than a
   deny-list, so the next forcing variable does not need a review round to find.
