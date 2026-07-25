<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-1-2-interfaces-null-engine-regression-harness-socket-deny.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 1.2: Interfaces, null engine, regression harness & socket-deny (C0c)'
type: 'feature'
created: '2026-07-13'
status: 'done'
baseline_revision: 'a559036bd1506f9a9fa785de8552e94b0be2c06e'
final_revision: 'eadb002e83'  # dev (5d25a9d2ec) + loop review cycle 1 (517677f3dc, 24 patches) + cycle 2 (eadb002e83, 15 patches), recovered onto claude/pdos-1-2-interfaces-null-engine after a bmad-loop stop/resume restart discarded the branch (2026-07-13)
review_loop_iteration: 3
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/epic-1-context.md'
warnings: [oversized, spec-reconstructed-post-restart]
---

<intent-contract>

## Intent

**Problem:** Story 1.1 froze the contract (model + schema + lattice) but nothing runs it: there is no `scan` pipeline, no engine seam for 1.3/1.5 to plug into, and no mechanical gate that polices false-green (C0c) and no-silent-egress (NFR-S2) for every later story.

**Approach:** Wire the skeleton end-to-end against a **null engine**: `typing.Protocol` interfaces for `extract`/`routing`/`engine`/`vuln-strategy`/`Policy`, a trivial single-manifest discovery stub, a minimal pyproject extractor, report assembly + JSON emission, and the real argparse CLI — plus the two-fixture regression harness (clean → green; false-green sentinel → ≥1 finding) and a deny-by-default socket harness over the whole test suite. Every future engine inherits these gates for free via the loop's verify command.

## Boundaries & Constraints

**Always:**
- **Producer, never editor:** `models.py`, `inventory.py`, `verdict.py`, and `data/report-schema.json` are the frozen 1.1 contract — read-only in this story.
- **Only `verdict.py` projects:** every exit code comes from `exit_code_for(...)` / `EXIT_SIGINT` (public names only). No exit literals `{1,2,130}`, no constants bound to them, no string-arg `sys.exit` in any new module — the 1.1 sole-ownership AST guard scans all new modules automatically and must stay green.
- **`engines.py` is the only subprocess-capable module** (the null engine spawns none); `extract/` is a **no-execution zone**: no `eval`/`exec`/`subprocess`/`os.system`/`jinja2` imports or calls; parsing via `tomllib` + `packaging.requirements` only.
- **Stream discipline (NFR-I3):** in `--format json`, stdout is exactly one valid `ComplianceReport` JSON document or empty — never partial/contaminated; all diagnostics go to stderr; `--format text` output is explicitly non-contract.
- **Determinism:** `json.dumps(report.to_json_dict(), sort_keys=True, ensure_ascii=True, indent=2, separators=(",", ": "))` — every dumps argument fixed; no `datetime.now()`; manifest paths in the report are relative to the scan target.
- **Zero new dependencies; do not touch `pixi.toml`, `pixi.lock`, or `pyproject.toml`.** The loop's verify gate runs `--frozen`, so a dependency change cannot even install. The socket-deny harness is hand-rolled (no `pytest-socket`).
- Strictly non-interactive: no prompts, never read stdin.
- All category values are `models.py` StrEnums (never bare literals); new data types are frozen dataclasses; `from __future__ import annotations` + full py3.12 hints, matching 1.1 style.
- Extend `tests/conftest.py` additively — the 1.1 `component_factory` fixture and existing tests keep passing untouched.

**Block If:**
- Satisfying an AC would require editing any frozen 1.1 artifact (schema, model fields, lattice/projection semantics, or new `Status`/`ErrorKind`/`WithholdReason` members) — that is a contract reopen, not a 1.2 decision.
- The clean-fixture→exit-0 / sentinel→≥1-finding pair cannot be expressed within the locked lattice and existing enum members.

**Never:**
- No `errors.py` exception hierarchy or no-scan guard (Story 1.7); no real engine runners or `_engine_env()` (1.3/1.5); no full FR1 discovery / multi-manifest / selection policy (1.9); no human renderer beyond a minimal text summary line (1.8 owns renderers); no `config.py`/ConfigLoader/policy tables (3.1); no `waiver.py` (3.2); no `sbom.py` (4.1); no `determinism.py` volatile-field machinery — `--deterministic` is accepted as a documented no-op flag (the report carries no volatile fields yet).
- No conda fixture and no real `conda_pypi_map.json` content (Story 2.1 owns the map's shape + generation) — the stub stays an empty mapping.
- No network access in any code path this story adds, runtime or test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean fixture | `scan tests/fixtures/projects/clean` (all deps `==`-pinned) | status `clean`, exit 0, findings `[]`, schema-valid JSON doc on stdout | — |
| False-green sentinel | `scan tests/fixtures/projects/sentinel` (one bare dep + one range-only dep) | status `indeterminate`, exit 1, ≥1 `indeterminate:<reason>:<pkg>` finding, `status.driver` non-null | never exit 0 |
| Empty dir | target exists, no `pyproject.toml` | status `not-applicable`, exit 0, `inventory_count` 0, empty `resolved_scan_set` | — |
| Nonexistent target | `scan /no/such/dir` | early fatal: stdout EMPTY (json mode), diagnostic on stderr, exit = `exit_code_for(ERROR)` (2) | no report emitted |
| Malformed manifest | `pyproject.toml` with invalid TOML | report still emitted: status `error`, exit 2, `ErrorRecord(kind=unparsable-manifest)`, driver present (`error:`-style id) | caught, fail-loud |
| Unparseable dep string | invalid PEP 508 entry among deps | component kept as `extraction_mode=raw-malformed`, withheld from vuln matching → indeterminate finding | never dropped silently |
| Twice-run | same fixture scanned twice (default AND `--deterministic`) | byte-identical stdout | — |
| Socket attempt | any test code opens an outbound connection | hard test failure (deny-by-default, no allowlist) | liveness meta-test proves the guard intercepts |
| `--version` / usage error | `--version`; unknown flag / no verb | version string + exit 0; usage on stderr + exit 2 — never 0 | argparse codes stay within `{0,2}` |
| SIGINT | `KeyboardInterrupt` during scan | exit `EXIT_SIGINT` (130), no `clean` report on stdout | deterministic unit test |

</intent-contract>

## Code Map

- `…/python_deptry_osv_scanner/models.py` -- FROZEN (1.1): StrEnums, `Finding`, `AxisCoverage`, `ErrorRecord`, `ScannedManifest`, `ComplianceReport.to_json_dict()`; read-only
- `…/python_deptry_osv_scanner/inventory.py` -- FROZEN (1.1): `Component`, `merge_components`, `ResolvedInventory`, `derive_purl`; read-only
- `…/python_deptry_osv_scanner/verdict.py` -- FROZEN (1.1): `compose`, `exit_code_for`, `match_level_rung`, `EXIT_SIGINT`; read-only
- `…/python_deptry_osv_scanner/data/report-schema.json` -- FROZEN (1.1) contract; read-only
- `…/python_deptry_osv_scanner/interfaces.py` -- NEW: the five Protocols + `EngineResult` + `DefaultPolicy`
- `…/python_deptry_osv_scanner/engines.py` -- NEW: engine registry + `NullEngine`
- `…/python_deptry_osv_scanner/routing.py` -- NEW: `Router` default impl (pypi classification)
- `…/python_deptry_osv_scanner/discovery.py` -- NEW: single-manifest stub
- `…/python_deptry_osv_scanner/extract/{__init__,pyproject}.py` -- NEW: minimal extractor (no-execution zone)
- `…/python_deptry_osv_scanner/mapping.py` + `data/conda_pypi_map.json` -- NEW: asset plumbing + stub map
- `…/python_deptry_osv_scanner/report.py` -- NEW: assembly + self-validate + JSON render
- `…/python_deptry_osv_scanner/cli.py` -- REWRITE the scaffold stub: real argparse + orchestration
- `…/tests/` -- conftest.py (extend), fixtures/projects/, conformance/, meta/, unit/; `test_smoke.py` updated

## Tasks & Acceptance

**Execution:** (all complete — see the recovered commits `5d25a9d2ec`/`517677f3dc`/`eadb002e83`)
- [x] `interfaces.py` — `EngineResult` (frozen) + `typing.Protocol` classes `Extractor`/`Router`/`Engine`/`VulnStrategy`/`Policy` + `DefaultPolicy` (withhold→indeterminate findings + driver-carrying rungs; `match_level_rung` rungs for assessable components)
- [x] `engines.py` — `register_engine`/`registered_engines` (deterministic) + `NullEngine` as the ONLY registered impl; sole future subprocess site
- [x] `routing.py` — `Router` default impl (pyproject `[project].dependencies` → PYPI; unknown kinds fail-loud)
- [x] `discovery.py` — single-manifest stub (`discover(target) -> tuple[ScannedManifest, ...]`, ≤1 entry, relative path, kind `"pyproject.toml"`, empty when absent)
- [x] `extract/{__init__,pyproject}.py` — `tomllib` + `packaging.requirements` extractor; `==`→concrete/`exact`; range/bare withheld; invalid string → `raw-malformed`; markers ignored; TOMLDecodeError → CLI-caught `ErrorRecord(unparsable-manifest)`; honest Gap-C fields + `merge_components`
- [x] `mapping.py` + `data/conda_pypi_map.json` — `importlib.resources` loader + `{}` stub (shape owned by 2.1)
- [x] `report.py` — `REPORT_SCHEMA_VERSION="1.0.0"`, `assemble_report(...)` (honest per-axis coverage, `deps_assessed=0` under null engine, `resolution_depth="direct-only"`, all-None `vuln_data`), `render_json` (pinned dumps args) + jsonschema self-validate before emit
- [x] `cli.py` — REWRITE: argparse `scan` verb, `--format {text,json}`, `--deterministic` no-op, `--version`; orchestration; NFR-I3 stream discipline; typed error-report branches; SIGINT→130; empty/nonexistent-target early-fatal
- [x] `tests/fixtures/projects/{clean,sentinel}/pyproject.toml` — 2 PyPI fixtures
- [x] `tests/conftest.py` — APPEND deny-by-default socket harness (autouse, import-time, resolver+UDP denials, no allowlist); 1.1 factory untouched
- [x] `tests/conformance/test_scan_harness.py` — regression harness (exit-code-matches, one-JSON-doc schema-valid, false-green=0, 0 uncaught, stderr-only, twice-run byte-identical incl. `--deterministic`, empty-dir + malformed-TOML rows)
- [x] `tests/meta/test_extract_no_execution.py` — AST denylist over `extract/` (guard-alive)
- [x] `tests/meta/test_socket_deny_alive.py` — liveness proof (conftest-fixture reachability)
- [x] `tests/unit/test_interfaces_and_null_engine.py` — registry/null-engine/DefaultPolicy unit coverage
- [x] `tests/unit/test_discovery_extract_cli.py` — matrix-edge unit coverage
- [x] `tests/test_smoke.py` — UPDATE to the real CLI surface

**Acceptance Criteria:**

*(Story 1.2 ACs from epics.md, preserved verbatim — the contract of record.)*

**Given** the completed scaffold, **When** `scan <trivial-dir>` runs with a **null engine**, **Then** it emits a schema-valid minimal `ComplianceReport` (from 1.1) to stdout and exits per the projection. **And** `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` exist as interfaces with the null engine as the only registered impl (**interface-first**). **And** a **trivial single-manifest discovery stub** ships here (enough for `scan <dir>` to locate one manifest) — completed/replaced by Story 1.9's full FR1 discovery.

**Given** `tests/conformance/`, **When** the harness runs, **Then** it has **2 PyPI fixtures** (one clean → green, one false-green sentinel → ≥1 finding) and asserts **0 uncaught exceptions + false-green=0 + exit-code-matches**. **And** the asset-loading plumbing + a stub `data/conda_pypi_map.json` exist. *(Both fixtures are PyPI — no conda fixture here, to avoid pulling 2.1's identity map into E1.)*

**Given** the **C0c socket-deny harness**, **When** any scan runs under test, **Then** any outbound socket attempt is a **hard test failure** (deny-by-default) — enforcing NFR-S2 for the null engine and every future engine without re-litigation.

*(Standing per-story gates, inherited from 1.1: the sole-ownership guard stays green over all new modules; twice-run byte-identical; all 1.1 tests keep passing unmodified.)*

## Spec Change Log

- **2026-07-13 — recovered post-restart.** The bmad-loop pilot run `20260713-060118-6606` produced this story as dev (`5d25a9d2ec`) + two loop review cycles (`517677f3dc`, 24 patches; `eadb002e83`, 15 patches — see commit messages for the finding summaries), all verified green (363 tests). Review cycle 3 stalled on a Fable 5 usage limit; a `bmad-loop stop`/`resume` to switch models restarted the story from scratch (dev attempt 2) and reset the branch, discarding the committed work from the branch (recoverable by SHA). The three commits were fast-forwarded back onto `claude/pdos-1-2-interfaces-null-engine`; `--frozen` verify → 363 passed. **This spec file was reconstructed from session context** (the gitignored Tier-3 original was on the wiped worktree); the cycle-1/cycle-2 triage-log detail lives in the commit messages. The pending cycle-3 review is being run as an Opus-backed pass with the standalone review tooling (see § Review Triage Log below).

## Review Triage Log

### 2026-07-13 — Dev-session inline review (Blind Hunter + Edge Case Hunter, deduplicated)
- intent_gap: 0 · bad_spec: 0 · patch: 19 (high 2, medium 6, low 11) · defer: 1 (medium) · reject: 3
- headline: engine-ErrorRecords-never-rung false-green (now `error` rung + `error:<kind>:<owner>` driver per engine error); newline-in-dep-name crash (id segments sanitize `\r`/`\n`); socket-deny holes (DNS/UDP/import-time egress) closed; `extract/` AST denylist widened; typed `UnparsableManifestError` split from internal-error.
- (committed as the dev base `5d25a9d2ec`)

### 2026-07-13 — Loop review cycle 1 (committed `517677f3dc`, 24 patches)
- exit-path catch-all, discovery fail-closed, hygiene-axis honesty, socket/AST guard widenings. Verified green.

### 2026-07-13 — Loop review cycle 2 (committed `eadb002e83`, 15 patches)
- findings-only-engine backstop (supersedes prior rejects), SystemExit/factory/extractor seam nets, discovery ENOTDIR fail-closed, AST network+asyncio.subprocess+star denylist, locale-independent error messages. Verified green.

### 2026-07-13 — Loop review cycle 3 (Opus, standalone 3-layer tooling — replaces the Fable-5-stalled loop cycle 3)
- Blind Hunter + Edge Case Hunter + Acceptance Auditor, all pinned to Opus (the Fable 5 usage limit is what stalled the in-loop cycle 3). Auditor: **3 of 3 ACs satisfied**, frozen-1.1 byte-equality confirmed, 0 violations.
- raw findings: 7 (blind 3, edge 4, auditor 0) → 6 unique after dedup (blind+edge both independently confirmed the closed-stdout bug empirically).
- patch: 5 (medium 1, low 4) — ALL applied + regression-tested; verify 363 → **368** green:
  - `[medium]` closed/replaced `sys.stdout` raises `ValueError` (not `OSError`) → escaped the emit guard → overrode the computed verdict with error-2 + traceback (exit-code sole-ownership violation). Emit guard now catches `(OSError, ValueError)`. (`cli.py`) — the real find three Fable-5 passes missed.
  - `[low]` NUL-byte scan path → `Path.stat()` raises `ValueError` → escaped to the internal-error traceback net. Stat guard now catches `ValueError` as an early-fatal user-input error. (`cli.py`)
  - `[low]` `_sanitize_id_segment` escaped only CR/LF → other line-boundary chars (`\x0b \x0c \x1c \x1d \x1e \x85 U+2028 U+2029`) split ids for line-oriented consumers. Now escapes the full `str.splitlines` set via `_LINE_BOUNDARY_ESCAPES`. (`interfaces.py`)
  - `[low]` `_socket` C-accelerator absent from the AST network denylist (direct `import _socket` bypass). Added. (`test_extract_no_execution.py`)
  - `[low]` guard-alive socket test omitted `gethostbyname_ex`/`gethostbyaddr` probes (patched in conftest but unprobed → a dropped patch line would regress silently). Both probes added. (`test_socket_deny_alive.py`)
- defer: 1 — Poetry/PDM deps outside `[project].dependencies` scan as not-applicable/exit-0 (residual false-green for exit-code CI); owned by Story 1.9's section-aware discovery (D2 split). Added to deferred-work.md + a CHARACTERIZATION test pinning the current behavior so 1.9 must consciously flip it.
- Recovered branch final: `--frozen` verify **368 passed** on `claude/pdos-1-2-interfaces-null-engine`.

## Design Notes

- **Interface shape:** `typing.Protocol` in one strategy-layer module (`interfaces.py`); the engine REGISTRY lives in `engines.py` (its stage module, the future sole-subprocess site).
- **Sentinel mechanism:** a null engine produces nothing; the sentinel's ≥1 finding comes from the fail-closed inventory path — withheld components (`indeterminate_reason` set by the extractor) become `indeterminate:<reason>:<pkg>` findings + driver rungs in `DefaultPolicy`. That is the C0 property the harness polices.
- **Coverage honesty under the null engine:** `deps_assessed=0` is truthful; the clean fixture still exits 0 in 1.2 by the AC's design — the "scanned nothing meaningful is never clean" tightening is Story 1.7's no-scan guard.
- **Socket-deny scope:** the tests-root `conftest.py` applies it suite-wide; engine subprocesses (1.3+) are naturally outside in-process patching (matches "network confined to named engine subprocesses").
- **Error-driver grammar** (`error:<kind>:<subject>`, dangling by design) is ceded to Story 1.7.

## Verification

**Commands:**
- `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` — expected: ALL tests pass (180 story-1.1 unmodified + all 1.2 suites). Recovered-branch result 2026-07-13: **363 passed**.
