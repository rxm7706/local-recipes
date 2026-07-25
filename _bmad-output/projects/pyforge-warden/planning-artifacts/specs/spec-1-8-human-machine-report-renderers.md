<!-- RECOVERED 2026-07-25 from Claude Code session transcript 2d5e330f-6952-4044-8b52-a4c284b6177e.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 1.8: Human & machine report renderers'
type: 'feature'
created: '2026-07-17'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-1-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `--format json` already emits the schema-valid `ComplianceReport` (Story 1.2's `render_json`), but `--format text` (the default) still emits one terse debug line (`status=... exit_code=... findings=N`) with no per-finding detail — not the "human summary (findings + verdict)" epics.md's story 1.8 AC requires. `--version`/`--help` and the chatty-engine + pseudo-TTY stdout-purity guarantee are already-shipped behavior (1.2/1.3) that this story must pin with regression coverage, not rebuild.

**Approach:** Add `render_text(report) -> str` to `report.py`, built from `report.to_json_dict()` (the same deterministically-sorted shape `render_json` already emits) — a verdict line plus one line per finding (axis, severity, id, message) and per error. Wire it into `cli.py`'s text branch through the same stream-guarded emission path `--format json` already uses. Add regression tests for `--help`, and for NFR-I3 stdout purity under a chatty engine + a pseudo-TTY stdout.

## Boundaries & Constraints

**Always:** `render_text` and `render_json` derive list ordering from `report.to_json_dict()` only — no second, independently-maintained sort. `--format text` output stays explicitly non-contract (free-format lines, not schema-validated) per `cli.py`'s existing doctrine; only `--format json` is schema-validated. Every finding line surfaces only what `Finding` already carries (`id`, `axis`, `subject`, `severity.tier`, `message`) — no invented fields. `verdict.py` stays the sole owner of status/exit-code projection; renderers never compute either.

**Block If:** Nothing here — every decision resolves from the frozen schema (`data/report-schema.json`), `to_json_dict()`'s existing sort contract, and epics.md's own story-level AC wording (all already evidenced in the codebase), not a human judgment call.

**Never:** Do not add a manifest-location or remediation-pointer field to `Finding`/`ComplianceReport`/the packaged JSON schema — the frozen 1.1 contract carries no such field, and `ComplianceReport` holds no `Component`/provenance data at all (only the manifest-level `resolved_scan_set`, not a per-finding pointer). FR17's epic-level summary phrasing ("package + manifest location + severity + remediation pointer") is superseded here by story 1.8's own AC text ("a human summary (findings + verdict)") — epics.md itself states story-level AC is authoritative over the epic-level FR table. Do not implement `--doctor` (FR29's D8 clause; realized in Story 5.1). Do not change `--format`'s default (`text`), the `--deterministic` no-op, or any exit-code literal.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--format text` (default), clean scan | CLEAN fixture | one verdict line (`warden: status=clean exit_code=0 findings=0`), no finding/driver lines | No error |
| `--format text`, findings present | a fixture with ≥1 finding (e.g. `DEPTRY_UNUSED`) | verdict line + one line per finding (axis, severity, id, message), in `to_json_dict()`'s sorted order | No error |
| `--format text`, errors present | a fixture forcing `Status.ERROR` | verdict line + one line per error (kind, owner, message) | typed, exit per verdict |
| `--format json` under a chatty engine + a pseudo-TTY stdout | `DEPTRY_UNUSED` fixture + `sys.stdout.isatty()` patched `True` | stdout is exactly one schema-valid JSON document — no engine chatter, no extra bytes (NFR-I3) | No error |
| `--version` | `["--version"]` | stdout `warden {version}\n`, exit 0 (already shipped) | argparse `SystemExit(0)` surfaced as rc 0 |
| `--help` | `["--help"]` | stdout contains usage text, exit 0 (already shipped, untested) | argparse `SystemExit(0)` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- MODIFY: add `render_text(report: ComplianceReport) -> str`, built from `report.to_json_dict()`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- MODIFY: import `render_text` from `.report`; replace the inline one-liner `print(...)` text branch with `sys.stdout.write(render_text(report) + "\n")` inside the existing stream-guarded emission block (unifies text/json emission through one BrokenPipe/OSError-guarded path).
- `src/shared/packages/pyforge-warden/tests/unit/test_report.py` -- MODIFY: add `render_text` unit tests (clean/header-only, findings present + ordering, driver line present/absent, errors present).
- `src/shared/packages/pyforge-warden/tests/conformance/test_scan_harness.py` -- MODIFY: add end-to-end `--format text` tests over clean/finding/error fixtures; add the chatty-engine + pseudo-TTY NFR-I3 regression test for `--format json`.
- `src/shared/packages/pyforge-warden/tests/unit/test_discovery_extract_cli.py` -- MODIFY: add `test_help_flag_exits_zero`, mirroring the existing `test_version_flag_exits_zero`.

## Tasks & Acceptance

**Execution:**
- [ ] `report.py` -- add `render_text` -- gives text mode a real human summary with the same deterministic ordering as JSON mode, no second sort implementation.
- [ ] `cli.py` -- wire `render_text` into the text branch through the shared guarded-emission path -- text and json now share one stream-failure-handling code path.
- [ ] `test_report.py` -- unit-test `render_text` in isolation (no CLI, no engines).
- [ ] `test_scan_harness.py` -- end-to-end `--format text` coverage + the NFR-I3 chatty-engine/pseudo-TTY regression test.
- [ ] `test_discovery_extract_cli.py` -- `--help` regression test.

**Acceptance Criteria** *(from epics.md, story 1.8)*:
- Given `--format text` (default), when run, then a human summary (verdict line + one line per finding) is emitted on stdout (FR17).
- Given `--format json`, when run, then a single valid schema-conformant `ComplianceReport` document is emitted on stdout (FR14) — already the case since Story 1.2, reconfirmed unchanged.
- Given `--format json` under a chatty-engine + pseudo-TTY fixture, when captured, then stdout is a single valid JSON document or empty — never contaminated (NFR-I3).
- Given `--version` or `--help`, when run, then a stable, zero-exit contract is emitted (FR31).
- Given any invocation, then exactly one exit code is produced (FR29) — already covered by the harness's existing rc-parity assertions across every fixture; no new test needed for this clause alone.

## Spec Change Log

## Review Triage Log

## Design Notes

**Why build `render_text` from `to_json_dict()` instead of iterating `report.findings`/`report.errors` directly:** `to_json_dict()` already owns the deterministic full-tuple sort (`render_json`'s byte-identical-output guarantee depends on it). Re-deriving a second sort in `render_text` risks the two renderers silently disagreeing on order across a future field-growth event; reusing the same dict keeps them mechanically in sync for zero extra cost. Example shape:

```
warden: status=warn exit_code=0 findings=1
  driver: axis=hygiene id=hygiene:DEP002:requests
  [hygiene] none hygiene:DEP002:requests -- requests defined as a dependency but not used
```

**Why no manifest-location field:** the frozen `Finding` dataclass (1.1) carries no component provenance, and `ComplianceReport` holds no `Component` objects at all — only `resolved_scan_set` (the manifest list) and `inventory_count`. Threading per-finding provenance onto `Finding` would be schema growth beyond what 1.1 sanctioned and is out of this story's scope (see Boundaries).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior suites unchanged + new `render_text`/`--format text`/NFR-I3/`--help` tests green.
- `pixi run --frozen -e local-recipes mypy src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new errors vs the Story-1.7-recorded baseline (10 pre-existing).
- `pixi run --frozen -e local-recipes ruff check src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new issues.
- Manual: `git diff --stat` shows zero changes to `verdict.py`, `models.py`, `data/report-schema.json`, and zero changes to any `Status`/`ErrorKind`/exit-code literal.
