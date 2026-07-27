<!-- RECOVERED 2026-07-25 from Claude Code session transcript 5ebb7fa7-4c1e-4abe-a838-51e00b960567.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 6.9: Fix-PR actuator (opt-in remediation PRs)'
type: 'feature'
created: '2026-07-24'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 6.1 froze an empty `actuation` slot on `ComplianceReport` for exactly this story, but nothing produces it: there is no `--open-fix-prs`/`--fix-prs-dry-run` flag, no `actuator.py`, no forge egress, and no wiring. FR40 (D12) needs an opt-in, post-verdict actuator that turns the run's findings into remediation pull requests (security → upgrade PRs; hygiene unused-dependency → removal PRs) without ever changing the verdict, exit code, or the scanned working tree.

**Approach:** Add a new `src/pyforge/warden/actuator.py` — the ONLY module permitted forge-API egress — that maps actuatable findings to `RemediationProposal`s (closed mapping: `vuln:` → `upgrade`, `hygiene:DEP002:` → `removal`; all other families ignored), then opens one PR per proposal via an injectable `ForgeClient` seam (default `GitHubForgeClient`: stdlib `urllib`, env-provided token/repo, the sole egress). `cli.py` — the sole invoker — runs it strictly after `rungs`/`findings` are final and before `assemble_report`, threading a JSON-serializable `actuation` payload into a new `assemble_report(actuation=...)` param (the frozen 6.1 slot; schema untouched). Dry-run shares the real code path up to the egress seam and opens no sockets. A per-story socket-deny carve-out, scoped to the actuator's real egress under the flag, lands here.

## Boundaries & Constraints

**Always:**
- `actuator.py` is the ONLY module permitted forge-API egress. It never imports `verdict.py` private names, never computes a rung or exit code, never spells the 7-rung lattice order — the `test_verdict_sole_ownership.py` guard stays green.
- `cli.py` is the sole invoker. The actuator runs after `rungs`/`findings` are finalized (post cli.py:1236) and before `assemble_report` (cli.py:1285), reading `findings` only. Its `actuation` payload flows ONLY into `ComplianceReport.actuation` — never into `rungs`, verdict composition, or exit projection. Order = compose-verdict-fixed → actuate → assemble → emit is honored because the verdict is a pure projection of the frozen `rungs` the actuator never touches.
- The scanned working tree is NEVER written (NFR-R3a). All remediation content is created forge-side (a fresh branch + a remediation commit) via the API; the local tree is only read.
- Forge credentials and repo identity come from the environment ONLY (`GITHUB_TOKEN` or `GH_TOKEN`; repo slug from `GITHUB_REPOSITORY`, else the git remote read-only), through an injectable `env` mapping (mirror `feeds.resolve_cache_dir`'s `env if env is not None else os.environ`). Never CLI flags.
- A failed PR-open (auth, network, API, or unresolved repo) is caught and recorded in `actuation` + echoed to stderr as a one-line summary. It NEVER raises, NEVER becomes an FR20 rung, NEVER changes status/exit code.
- `--fix-prs-dry-run` shares the real code path up to the egress seam, records intent in the same `actuation` section, and opens NO sockets. If both flags are given, dry-run wins.
- The socket-deny carve-out is scoped to `actuator.py`'s real egress via an egress marker the actuator sets ONLY on the real path; inert on dry-run and without the flag; never a global loosening. `tests/meta/test_socket_deny_alive.py` stays green (deny is still the default everywhere else).
- Remediation mapping is closed: `vuln:<advisory>:<pkg>@<ver>` → `upgrade`; `hygiene:DEP002:<pkg>` → `removal`; every other finding family (missing/transitive/misplaced hygiene, license, currency, indeterminate sentinels) yields NO proposal. Each PR body carries the finding id + a report excerpt built from the `Finding` (id, message, severity, advisory) + the recommended action.
- No-flag runs stay byte-identical to pre-6.9. `models.py`, `report-schema.json`, `verdict.py`, and every axis producer stay UNTOUCHED — the `actuation` slot is already frozen open (populate, don't edit).
- The `actuation` payload is JSON-serializable and deterministically ordered (sorted by finding id); volatile fields (PR url, any timestamp) are isolated to clearly-named fields.

**Block If:**
- The scoped socket-deny carve-out cannot be implemented without loosening the global deny default (no narrow actuator-only mechanism works) → HALT `blocked`, condition `carve-out cannot stay actuator-scoped` (violates the binding architecture.md:137 rule).

**Never:**
- Never write or edit the local scanned tree or its manifests.
- Never re-run osv-scanner or query OSV/the network to compute a fixed version (offline default). The upgrade PR cites the advisory and does NOT assert a computed target version — precise target-version resolution and safe multi-format manifest editing are deferred to the ledger (v1.x).
- Never add a field to `Finding`/`ComplianceReport` or edit `report-schema.json`/`models.py` (schema frozen by 6.1).
- Never let `actuation` influence status/exit; never compute an exit code in `actuator.py`.
- No new third-party runtime dependency — forge egress uses stdlib `urllib` (mirror `scripts/refresh_*_feed.py`'s `Request(url, headers={"User-Agent": ...})` + `urlopen(..., timeout=...)  # noqa: S310` shape).
- Not building `determinism.py`/`--deterministic` here (separate future work); just preserve no-flag byte-identity and keep the actuator out of the twice-run byte-identity fixtures.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dry-run, actuatable findings | scan with a `vuln:` + a `hygiene:DEP002:` finding, `--fix-prs-dry-run` | `actuation` lists 2 proposals (`upgrade`/`removal`), outcome `planned`; NO socket opened; verdict/status/exit-code identical to the no-flag run; stdout stays ONE document | No error expected |
| Real open, creds present | findings present, `GITHUB_TOKEN`+`GITHUB_REPOSITORY` in env, `--open-fix-prs` | one PR per proposal opened via the forge API; `actuation` records `opened` + pr_url; exit code unchanged | API/network failure → per-proposal `failed` in `actuation` + stderr line; exit unchanged |
| Duplicate PR | an open PR already exists for a finding id | that proposal recorded `skipped`; no duplicate opened | No error expected |
| No creds / no repo | `--open-fix-prs`, no token or unresolvable repo slug | opens nothing; a single `failed` resolution record in `actuation` + stderr; exit unchanged | Loud, never raises |
| Neither flag | normal scan | `report.actuation` is `None`; output byte-identical to pre-6.9 | No error expected |
| Non-actuatable only | only license/currency/indeterminate/other-hygiene findings, `--fix-prs-dry-run` | `actuation` has zero proposals; no PRs | No error expected |
| Blocking + real open | critical `vuln:` → `policy-violation`, `--open-fix-prs` | actuator runs; exit code stays non-zero (false-green stays 0); actuation records the open | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/warden/actuator.py` -- **new**, the sole forge-egress module. `RemediationProposal(finding_id, action, subject, title, body)` (frozen); `PROutcome(finding_id, action, subject, status, pr_url, detail)` where `status ∈ {"planned","opened","skipped","failed"}`; `Actuation(dry_run, outcomes)` with `to_json_dict()` returning a sorted-by-finding-id dict. `plan_remediations(findings) -> tuple[RemediationProposal, ...]` (pure, closed mapping). `ForgeClient` Protocol: `existing_open_pr(finding_id) -> str | None`, `open_pull_request(proposal) -> str` (returns pr_url). `GitHubForgeClient` (default): stdlib `urllib`, `resolve_forge(env)` for token+repo, the only place a socket opens, guarded by an egress marker (e.g. a module-level `contextvars.ContextVar` `_EGRESS_ACTIVE` set only around real requests). `run_actuator(findings, *, dry_run, env=None, client=None) -> Actuation`: builds the plan; dry-run records `planned` and instantiates/calls NO client; real path dedups via `existing_open_pr` then `open_pull_request`, catching every exception into a `failed` outcome (never raises). No import of `verdict`; no exit-code logic.
- `src/pyforge/warden/report.py` -- `assemble_report(..., actuation: object | None = None)` new keyword param threaded verbatim into `ComplianceReport(actuation=actuation)` (models.py:748 already serializes it pass-through). `render_text` gains an `actuation` param and a terse `[actuation]` block (one line per outcome: `[actuation] <status> <action> <finding_id>[ -> <pr_url>]`) after the existing suppression/waiver blocks, present only when `actuation is not None`. Compose/verdict path unchanged.
- `src/pyforge/warden/cli.py` -- `scan.add_argument("--open-fix-prs", action="store_true", ...)` and `"--fix-prs-dry-run"` near cli.py:628. After cli.py:1236 (rungs final), before cli.py:1285: if either flag set, `actuation = run_actuator(findings, dry_run=args.fix_prs_dry_run or not args.open_fix_prs, env=os.environ)`; thread `actuation.to_json_dict()` into `assemble_report(actuation=...)` and `render_text(actuation=...)`; if any outcome is `failed`, write a one-line stderr summary (mirroring the `bypass_stanza`/`baseline_stanza` stderr routing at cli.py:1345-1355, keeping stdout pure). Import from `.actuator`.
- `tests/conftest.py` -- extend the module-level socket-deny harness (conftest.py:89-208) with a narrow carve-out that permits `connect`/`create_connection` ONLY while `actuator._EGRESS_ACTIVE` is set (and only to a loopback test host), so a real-path test can drive `GitHubForgeClient` against a threaded local `http.server`. Deny stays the default; the marker is set only by the actuator's real egress.
- `tests/unit/test_actuator.py` -- **new**: `plan_remediations` mapping (vuln→upgrade, DEP002→removal, others→none); dry-run builds `planned`, instantiates no client, opens no socket; real path with a fake `ForgeClient` records `opened`; dedup → `skipped`; failed open caught → `failed`, never raised; `resolve_forge` env reading incl. unresolved → `failed` record; `Actuation.to_json_dict()` sorted + JSON-serializable; never-writes-tree (tmp_path snapshot unchanged).
- `tests/conformance/test_fix_pr_actuator.py` -- **new**, E2E via `cli.main(["scan", ...])`: dry-run populates `actuation` in JSON + text, opens no socket, leaves verdict/status/exit identical to the no-flag run, stdout ONE pure document; real `--open-fix-prs` against a local fake forge (under the carve-out) records `opened`; a forge failure leaves exit unchanged + a stderr line; duplicate → `skipped`; blocking findings + `--open-fix-prs` still exit non-zero; no-flag run byte-identical to pre-6.9.
- `tests/meta/test_socket_deny_alive.py` -- add an assertion that the carve-out is inert without the actuator marker (sockets stay denied outside real egress).

(All paths above are relative to `src/shared/packages/pyforge-warden/`.)

## Tasks & Acceptance

**Execution:**
- [ ] `src/pyforge/warden/actuator.py` -- `RemediationProposal`/`PROutcome`/`Actuation` + `plan_remediations` + `ForgeClient`/`GitHubForgeClient` + `run_actuator` -- the sole forge-egress module, closed mapping, catch-all failure capture
- [ ] `src/pyforge/warden/report.py` -- `assemble_report(actuation=...)` + `render_text` `[actuation]` block -- populate the frozen 6.1 slot, human-visible
- [ ] `src/pyforge/warden/cli.py` -- `--open-fix-prs`/`--fix-prs-dry-run` flags + post-verdict/pre-assemble invocation + stderr failure summary -- gate activation end-to-end, order-correct
- [ ] `tests/conftest.py` + `tests/meta/test_socket_deny_alive.py` -- actuator-scoped socket carve-out + inert-without-marker assertion -- C0c carve-out, never global
- [ ] `tests/unit/test_actuator.py` -- mapping/dry-run/real/dedup/failure/env/never-writes-tree coverage
- [ ] `tests/conformance/test_fix_pr_actuator.py` -- E2E dry-run + real + failure + duplicate + false-green + byte-identity proof

**Acceptance Criteria:**
- Given `--open-fix-prs` with env forge credentials, when the verdict has been composed (exit fixed), then `cli.py` runs the actuator, opens an upgrade PR per `vuln:` finding and a removal PR per `hygiene:DEP002:` finding via the forge API (finding id + report excerpt in the body), then assembles + emits the report including the `actuation` section — and the scanned working tree is never written.
- Given `--fix-prs-dry-run`, when the actuator runs, then it shares the real code path up to the egress seam, writes its intent into the `actuation` section, opens no sockets, and leaves stdout a single pure document.
- Given a failed PR-open (or an existing open PR for the same finding id), when the actuator runs, then the failure/skip is recorded in `actuation` + stderr and never changes verdict, status, or exit code; a duplicate is skipped, never re-opened.
- Given no `--open-fix-prs`/`--fix-prs-dry-run` flag, when the scan runs, then `report.actuation` is `None` and every pre-6.9 fixture is byte-identical; `verdict.py`, `models.py`, and `report-schema.json` stay untouched.
- Given blocking findings and `--open-fix-prs`, when the scan runs, then the exit code stays non-zero (false-green stays zero) and the socket-deny meta-test stays green (carve-out inert outside the actuator's real egress).

## Design Notes

The verdict is a pure projection of the finalized `rungs`; the actuator reads only `findings` and writes only the pass-through `actuation` slot, so "compose-fixed → actuate → assemble" and "a failed PR-open never changes the exit code" both hold by construction — no need to move `compose` out of `assemble_report`.

Fixed-version data is genuinely unavailable in-memory (the security engine discards OSV `ranges/events` fixed bounds, and `Finding` is schema-frozen), so an `upgrade` PR cites the advisory + current vulnerable version and requests the bump; it does not assert a computed target version. Producing an actual manifest diff (safe multi-format editing + exact upgrade targets) is deferred — the v1 PR carries the actionable finding into the repo's PR workflow for a human to complete.

Egress marker / carve-out shape (illustrative):
```python
# actuator.py
_EGRESS_ACTIVE: ContextVar[bool] = ContextVar("_EGRESS_ACTIVE", default=False)
# GitHubForgeClient wraps each real urllib call in `_EGRESS_ACTIVE` set True.
# conftest.py deny-hook: permit connect() only when _EGRESS_ACTIVE.get() and host is loopback.
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green including the new `test_actuator.py` + `test_fix_pr_actuator.py`; the verdict sole-ownership and socket-deny meta-tests green; no-flag and dry-run behavior byte-identical to pre-6.9 on existing fixtures. (Canonical `--frozen` form per `deferred-work.md`'s worktree path-length note.)
