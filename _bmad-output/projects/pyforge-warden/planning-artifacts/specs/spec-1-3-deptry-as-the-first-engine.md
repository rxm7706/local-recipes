<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-1-3-deptry-as-the-first-engine.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 1.3: deptry as the first engine (hygiene findings)'
type: 'feature'
created: '2026-07-13'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
baseline_revision: 'cd65065a5143690ea4905bee981d45685ffafbeb'
final_revision: 'c509c18fa3'  # dev 3e9f0bcf1e + independent Opus review cycle (c509c18fa3): DEP001->warn + 5 robustness/determinism patches
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 1.2 wired the skeleton end-to-end against a *null* engine — the `Engine` seam exists but nothing real runs through it, and the hygiene axis is inert (`deps_assessed=0`, DefaultPolicy sends every finding to a conservative `indeterminate` backstop). No dependency-hygiene results reach the report.

**Approach:** Stand up **deptry** as the first real engine through a load-bearing `_engine_env()` subprocess-normalization seam (temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`, argv-only, bounded timeout, utf-8-decode→typed-error), parse its `--json-output` DEP001–005 records into `hygiene:<code>:<subject>` Findings via a new `hygiene.py`, replace the indeterminate backstop for **hygiene-axis** findings with the real default hygiene→status table (DEP001 → **warn** in 1.3 — its Gap-A block is gated on Story 2.1's name-mapping confidence, per the follow-up Opus review; DEP002/3/4/5 → warn), and wire real hygiene coverage (`deps_assessed`) into the report. deptry's exit code is never the gate; the verdict reads report content.

## Boundaries & Constraints

**Always:**
- **Producer, never editor:** `models.py`, `inventory.py`, `verdict.py`, and `data/report-schema.json` are the frozen 1.1 contract — read-only. `hygiene:<DEP-code>:<subject>` ids and the `hygiene` axis already exist in that schema; emit within it. **No new `Status`/`ErrorKind`/`WithholdReason` members.**
- **Only `verdict.py` projects exit codes / owns the lattice.** New `hygiene.py` and edited modules produce `(Status, StatusDriver)` rungs only — no exit literals `{1,2,130}`, no constant bound to them, no spelling of the 7-rung order (the sole-ownership AST guard auto-scans `hygiene.py`).
- **`engines.py` is the only subprocess-capable module.** Every engine call goes through `_engine_env()`: argv **list** (never `shell=True`, never manifest data as a flag), machine output forced to a `tempfile.mkstemp`/`mkdtemp` file (`0600`/`0700`) in **system temp — never the scanned tree**, deptry's own stdout/stderr **discarded** (`DEVNULL`) — its machine output is read from the `-o` temp file, so deptry chatter never reaches our streams (BH7 superseded the earlier "diagnostics sink" phrasing), `NO_COLOR=1` + `--no-ansi`, `stdin=DEVNULL`, bounded configurable subprocess timeout, explicit `encoding="utf-8"` decode with undecodable/JSON-broken output → typed `ErrorRecord` (never a traceback, never a silent drop). Temp files cleaned up on success **and** failure.
- **Exit code is content, never returncode.** deptry exit 1 (issues found) is expected and ignored; the verdict reads report content. deptry crash-with-no-output → typed `ErrorRecord` → `error`/exit 2, report still emitted — never empty-clean.
- **FR9 honored natively:** run `deptry <target>` so deptry reads the project's own `[tool.deptry]` (`ignore`/`per_rule_ignores`/`exclude`/`extend_exclude`) — do **not** re-implement ignore logic or point `--config` elsewhere.
- **Determinism:** sort hygiene findings by id before emit; never iterate a set for output; twice-run byte-identical (default and `--deterministic`).
- **Zero new dependencies; do not touch `pixi.toml`, `pixi.lock`, or `pyproject.toml`.** deptry + osv-scanner are already conda run-deps; the verify gate runs `--frozen`.
- Category values are `models.py` StrEnums (never bare literals); new data types are `@dataclass(frozen=True)` with `from __future__ import annotations` + full py3.12 hints, matching 1.1/1.2 style. Extend `tests/conftest.py` additively.

**Block If:**
- Satisfying an AC would require editing a frozen 1.1 artifact (schema, model fields, lattice/projection, or a new enum member) — that is a contract reopen, not a 1.3 decision.
- deptry's real DEP-code set on the pinned range diverges from DEP001–005 such that the finding-id grammar or hygiene→status table cannot represent it within the frozen schema.

**Never:**
- No vuln/CVSS severity gate, no two-axis end-to-end composition, no `warn_is_error` configurability (Story 1.6); no `config.py`/`ConfigLoader` (Story 3.1) — the hygiene→status table lives as a **module default in `hygiene.py`**, which 3.1 later lifts to an overridable config table.
- No `errors.py` exception hierarchy / no-scan guard (1.7) — typed failures surface via `EngineResult.errors` (`ErrorRecord`), not a new exception tree.
- No `osv-scanner` runner (1.5), no `determinism.py` (`--deterministic` stays a documented no-op — no volatile fields yet), no full FR1 discovery / multi-manifest (1.9), no human renderer beyond the existing summary line (1.8).
- **Do not consult the conda→pypi map** for the DEP001 confidence gate. In 1.3 DEP001 → **warn** (not block): Gap-A requires DEP001 blocking to be gated on name-mapping confidence, but that signal needs Epic 2's conda→pypi map (the stub stays `{}`), and deptry's DEP001 false-positives (guarded optional imports) make an ungated block a benign false-red. Story 2.1 supplies the map and upgrades DEP001 to block-on-high-confidence (follow-up Opus review, 2026-07-14).
- No subprocess-level network sandbox: the in-process socket-deny harness cannot patch a child process, and deptry needs no network. AC3's gate is satisfied by (our orchestration opens no socket → harness stays green) + (deptry runs offline in tests).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean under deptry | project whose `==`-pinned deps are all imported | status `clean`, exit 0, findings `[]`, hygiene `deps_assessed == deps_total` (> 0) | — |
| Missing dep (DEP001) | source imports a module neither declared nor installed | `hygiene:DEP001:<module>` finding (axis `hygiene`, subject=module), status `warn`, exit 0, driver axis `hygiene` — still surfaced, never false-green (2.1 upgrades to block-on-high-confidence) | — |
| Unused dep (DEP002) | dep declared, never imported | `hygiene:DEP002:<pkg>` finding → `warn`, exit 0 | — |
| Stdlib dep (DEP005) | a stdlib module (e.g. `argparse`) declared as a dependency | `hygiene:DEP005:<pkg>` finding → `warn`, exit 0 (**DEP005 = stdlib, not "unused-dev"**) | — |
| `[tool.deptry]` ignore | pyproject with `[tool.deptry] ignore=["DEP002"]` + an otherwise-DEP002 project | deptry suppresses DEP002 natively → no such finding; status per remaining content | — |
| Chatty/ANSI deptry output | deptry prints warnings/ANSI to its own streams | our stdout is exactly one schema-valid JSON doc (json mode) — read from the `-o` temp file, not deptry's stdout; deptry noise → **discarded** (its streams are `DEVNULL`, BH7) | — |
| deptry binary absent | `deptry` not on PATH (subprocess `FileNotFoundError`) | `EngineResult.errors` = `ErrorRecord(kind=engine-unavailable, owner="deptry")` → status `error`, exit 2, report still emitted | never silent PASS |
| deptry timeout | subprocess exceeds the bounded timeout | `ErrorRecord(kind=engine-timeout, owner="deptry")` → `error`, exit 2, no hang (tested via injected fake, not a real sleep) | fail-loud |
| Undecodable / malformed deptry JSON | non-utf8 bytes, or a record missing `error.code`/`module`, or non-array JSON | `ErrorRecord(kind=engine-output-unparseable\|-unrecognized, owner="deptry")` → `error`/exit 2; the record is counted toward `unparseable_rate`, never dropped silently | never empty-clean |
| Socket attempt during scan (our code) | any orchestrator code opens an outbound connection under test | hard test failure (deny-by-default harness holds) | — |
| Twice-run | same fixture scanned twice (default and `--deterministic`) | byte-identical stdout | — |

</intent-contract>

## Code Map

- `…/python_deptry_osv_scanner/models.py` · `inventory.py` · `verdict.py` · `data/report-schema.json` -- FROZEN (1.1): read-only. `hygiene` axis + `hygiene:<code>:<subject>` id family + `WARN`/`POLICY_VIOLATION` statuses + engine `ErrorKind`s already exist here.
- `…/python_deptry_osv_scanner/engines.py` -- EDIT: add `_engine_env()` normalization helper + `DeptryEngine(Engine)` (invokes deptry via `_engine_env`, returns `EngineResult(findings, errors, coverage)`); register it. Retain `NullEngine` class (its unit tests unchanged).
- `…/python_deptry_osv_scanner/hygiene.py` -- NEW (E2): parse deptry JSON → hygiene `Finding`s (per-code join: DEP001→subject=module/no component; DEP002/3/4/5→subject=declared name); `DEFAULT_HYGIENE_POLICY` table (code→`Status`); rung derivation; `unparseable_rate` accounting + `UNPARSEABLE_RATE_BASELINE`.
- `…/python_deptry_osv_scanner/interfaces.py` -- EDIT: `DefaultPolicy.evaluate` routes **hygiene-axis** engine findings through the hygiene table (tighten-only, replaces the indeterminate backstop for that axis); non-hygiene findings keep the 1.2 backstop.
- `…/python_deptry_osv_scanner/report.py` -- EDIT: `assemble_report` merges per-axis coverage from `engine_results` (hygiene `deps_assessed` no longer hardcoded 0); keyword-only, additive.
- `…/python_deptry_osv_scanner/cli.py` -- EDIT: thread `engine_results` into `assemble_report`; orchestration order otherwise unchanged (deptry runs at the existing engine seam).
- `…/tests/fixtures/projects/clean/` -- EDIT: add a source module importing its declared deps so it is genuinely clean under deptry.
- `…/tests/fixtures/projects/{deptry_missing,deptry_unused,deptry_stdlib,deptry_ignore}/` -- NEW deptry end-to-end fixtures.
- `…/tests/unit/test_hygiene.py` -- NEW: synthetic-deptry-JSON unit tests for the full DEP001–005 (+unknown-code, +malformed-record) → status table, join, determinism, `unparseable_rate`.
- `…/tests/unit/test_engine_env_deptry.py` -- NEW: `_engine_env` seam (temp-file/NO_COLOR/stdin=DEVNULL/argv-only/cleanup) + timeout→typed + unavailable→typed, via injected fakes.
- `…/tests/conformance/test_scan_harness.py` -- EDIT: add the deptry fixture rows; keep clean→0-findings (post-fixture fix); make sentinel assertions tolerant of deptry's added DEP002 warns (indeterminate still wins) or silence deptry there; add the `unparseable_rate ≤ baseline` ratchet assertion.

## Tasks & Acceptance

**Execution:**
- [x] `engines.py` -- add `_engine_env()` (temp-file mkstemp/mkdtemp 0600/0700 in system temp, `NO_COLOR=1`, `--no-ansi`, `stdin=DEVNULL`, argv list, bounded timeout, utf-8 decode → typed `ErrorRecord`, cleanup on success+failure) + `DeptryEngine` (argv `["deptry", str(target), "-o", <tempfile>, "--no-ansi"]`, exit code ignored, `FileNotFoundError`→engine-unavailable, `TimeoutExpired`→engine-timeout); register via `register_engine`. Adjust any registry-content assertion.
- [x] `hygiene.py` -- NEW: `parse_deptry_output(raw) -> DeptryParse` (findings + `records_total`/`records_unparseable`/`unparseable_rate`; malformed record → counted + `ErrorRecord(engine-output-unrecognized)`, never dropped); `DEFAULT_HYGIENE_POLICY = {DEP001: POLICY_VIOLATION, DEP002/3/4/5: WARN}` with unknown-code default `INDETERMINATE` (never false-green); rung derivation building `StatusDriver(axis="hygiene", finding_id=...)`; finding id = `hygiene:<code>:<_sanitize_id_segment(module)>`, `subject`=raw module.
- [x] `interfaces.py` -- route hygiene-axis findings through `hygiene.py`; keep vuln-axis + component-derived paths unchanged.
- [x] `report.py` -- merge engine per-axis coverage into `assemble_report` (hygiene `deps_assessed` from `DeptryEngine`'s `EngineResult.coverage`).
- [x] `cli.py` -- pass `engine_results` to `assemble_report`.
- [x] fixtures -- fix `clean/` (import its deps); add `deptry_missing/`, `deptry_unused/`, `deptry_stdlib/`, `deptry_ignore/`.
- [x] `tests/unit/test_hygiene.py` + `tests/unit/test_engine_env_deptry.py` -- NEW (matrix + seam coverage, injected fakes; no real network/sleep).
- [x] `tests/conformance/test_scan_harness.py` -- deptry rows + ratchet assertion; clean/sentinel assertions reconciled.

**Acceptance Criteria:**

*(Story 1.3 ACs from epics.md, preserved verbatim — the contract of record.)*

**Given** a PyPI project with a missing/unused dependency, **When** I run `scan .`, **Then** deptry runs via `_engine_env()` (temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`, argv-only) and its DEP001–005 findings land in the `ResolvedInventory` (FR8, and FR4 native-parser delegation). **And** deptry's exit code is **never** the gate — the verdict reads report content.

**Given** deptry emits chatty/ANSI output, **When** captured, **Then** stdout stays a single valid JSON document (the pure-JSON stdout seam) and diagnostics go to stderr. **And** the ratchet mechanism (`unparseable_rate` baseline) is introduced.

**Given** a project with a `[tool.deptry]` config, **When** scanned, **Then** those ignores are honored (FR9). **And** the C0c socket-deny gate holds (deptry runs with no egress). **And** DEP005's actual semantics are **verified against the pinned deptry range** (the pinned-contract label "unused-dev" may itself be wrong) and a DEP005 → `warn` row is added to the ConfigLoader hygiene policy table (added 2026-07-12).

*(Standing per-story gates, inherited from 1.1/1.2: the verdict.py sole-ownership guard stays green over `hygiene.py` and all edited modules; false-green = 0 on the slice's fixtures; twice-run byte-identical; all prior 1.1/1.2 tests keep passing.)*

### 2026-07-14 — Independent Opus review cycle (Blind Hunter + Edge Case Hunter + Acceptance Auditor, standalone tooling, all on Opus)
Ran because story 1.1/1.2's independent passes each caught a real bug the inline review missed — this one did too (a high). Auditor: **2 of 3 ACs** (the 2 gaps are AC-wording/spec-reconciliation, not code defects). raw 13 (blind 5, edge 4, auditor 4) -> 6 unique after dedup.
- **[high][user-decision] DEP001 -> warn** (was policy-violation). Gap-A requires DEP001's block to be GATED on conda<->PyPI name-mapping confidence, which needs Story 2.1's map; ungated + deptry's optional-import false-positives = benign false-red. User chose warn-until-2.1 (still surfaced, never false-green; 2.1 upgrades to block-on-high-confidence). Table + docstring + `deptry_missing` fixture/test updated.
- **[medium][patch] twice-run determinism**: the unrecognized-record error message baked deptry's array **index** -> non-byte-identical stdout (NFR-I3). Index removed; count carried in `unparseable_rate`.
- **[low][patch] colon-bearing DEP code** slipped past the id-grammar guard into a mangled indeterminate finding -> now UNRECOGNIZED (grammar-checked); a well-formed unknown code (DEP006) still degrades gracefully to indeterminate.
- **[low][patch] TOCTOU vanished cwd** misreported as "binary not found on PATH" -> disambiguated to `engine-execution-failed` (the `_engine_env` seam 1.5 reuses).
- **[low][patch] empty `-o` output** misreported as "invalid JSON" -> distinct "no machine output" diagnostic (surfaces a deptry version/flag skew).
- **[patch] AC2 spec reconcile**: two normative sections claimed a "diagnostics sink"; code discards deptry streams (`DEVNULL`, BH7). Always + I/O-matrix rows corrected (the epic AC "diagnostics -> stderr" refers to OUR diagnostics, which holds).
- **defer (2)**: (a) unrecognized record *shape* -> error/exit-2 has zero forward-tolerance (a future deptry field flips scans to false-error) — bounded by the deptry conda pin, deferred as a forward-compat hardening; (b) `deps_assessed == inventory.count` over-claims coverage when deptry resolves nothing -> Story 1.7 no-scan guard (already a residual risk). Both in deferred-work.md.
- **bonus**: the 1.2 Poetry-deps false-green is RESOLVED here — deptry reads `[tool.poetry]` natively (that 1.2 characterization test was legitimately rewritten to expect warn/DEP002).
Verify: **429 passed** (`--frozen`, worktree); frozen 1.1 artifacts + manifests untouched.

## Design Notes

- **DEP005 = stdlib dependency (verified against deptry 0.25.1, 2026-07-13):** message `'argparse' is defined as a dependency but it is included in the Python standard library.` The architecture's pinned label "unused-dev" is wrong; `DEP005 → warn` is still the correct ceiling. Deptry codes on the pinned range: DEP001 missing / DEP002 unused / DEP003 transitive / DEP004 misplaced-dev / DEP005 stdlib.
- **The clean-fixture hazard (verified):** the 1.2 `clean/` fixture declares `requests`/`packaging` but imports neither → deptry emits **DEP002 × 2** → not clean. Once `DeptryEngine` registers, the conformance `clean→0-findings/exit-0` row would break. Fix the fixture to import its deps. The `sentinel/` fixture (`leftpad` bare + `requests>=2.0` range) additionally draws DEP002 warns from deptry, but the extractor's `indeterminate` rungs still dominate the lattice (indeterminate > warn) → status/exit unchanged; make the harness assertion tolerant (filter reasons to the `indeterminate:` family) or add `[tool.deptry] ignore` there.
- **`_engine_env()` is load-bearing and ruinous to retrofit** — build it correctly now; osv (1.5) reuses it verbatim. Read the `-o` **file**, never deptry's stdout (that is the pure-JSON-seam guarantee for AC2). deptry writes only to our system-temp file → the scanned tree is never mutated (NFR-S4).
- **DefaultPolicy tighten-only:** the 1.2 backstop sent every engine finding to `indeterminate`. 1.3 replaces that *for the hygiene axis only* with `DEFAULT_HYGIENE_POLICY`; unknown codes still degrade to `indeterminate` (additive-growth safety). Example rung: `("policy-violation", StatusDriver("hygiene", "hygiene:DEP001:totally_absent_pkg_xyz"))`.
- **Coverage seam:** `EngineResult.coverage` was deliberately discarded in 1.2. `assemble_report` now uses an engine's per-axis `AxisCoverage` when present (hygiene → deptry's `deps_assessed == inventory.count` on success), else the default (vuln axis stays `deps_assessed=0` until 1.5).
- **FR9 is free** (verified: `[tool.deptry] ignore=["DEP002"]` → `[]`/exit 0). **DEP001 confidence gate:** PyPI-native = high confidence → block; do not read the stub conda map (Epic 2 owns the ambiguous→warn branch).
- **Ratchet (NFR-R2):** `parse_deptry_output` exposes `unparseable_rate` (structurally-unmappable records ÷ total); `UNPARSEABLE_RATE_BASELINE = 0.0`; a conformance assertion pins `rate ≤ baseline` on the deptry corpus (ratchet may only decrease). A malformed record is counted **and** surfaces a typed `ErrorRecord` (never a silent drop).

## Verification

**Commands:**
- `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` -- expected: all prior 1.1/1.2 suites + the new deptry unit/seam/conformance suites pass; false-green = 0; twice-run byte-identical. (`--frozen` is mandatory in the loop worktree — see `deferred-work.md`: the unfrozen solve panics and rewrites `pixi.lock`.)
- Sole-ownership + no-execution + socket-deny meta-tests stay green with `hygiene.py` present.

## Review Triage Log

### 2026-07-13 — Review pass (Blind Hunter + Edge Case Hunter, Opus)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 5
- reject: 9
- addressed_findings:
  - `[low]` `[patch]` EC1 (BOM): `_engine_env` decodes deptry's machine output with `utf-8-sig` — a leading BOM some tools prepend no longer false-fails a clean run as `engine-output-unparseable`; genuinely non-utf-8 bytes still raise.
  - `[low]` `[patch]` BH7 (dead PIPE + doc drift): child stdout/stderr routed to `DEVNULL` (no in-memory buffering of discarded chatter); docstring corrected (dropped the false "diagnostics sink" claim).
  - `[low]` `[patch]` BH10 (doc/impl mismatch): reworded the `DEPTRY_TIMEOUT_SECONDS` comment — it is a fixed default (override via the `_engine_env` `timeout` param; user-facing config surface lands in Story 3.1), not a wired config.
  - Deferred (→ deferred-work.md): BH1 deptry env-coupling; BH3+BH4 `deps_assessed` coverage proxy (owned by 1.7 no-scan guard / 1.9 discovery); BH11 shared id-grammar module extraction; BH5 seam returncode contract (owned by 1.5, with osv 127/128).
  - Rejected (noise/by-design): BH2 (DEP002/3/4→warn is per FR18/architecture; C0 preserved), BH6 (fixtures env-robust; hard-fail on absent provisioned deptry is correct), BH8 (post-reap unlink succeeds; negligible), BH9 (`-o` is deptry's stable documented alias; test churn not worth it), BH12 (sentinel codes stable; the suggested alt would add a DEP001 for unpinned `leftpad`), BH13 (deptry JSON messages are literal English; chatter is DEVNULL'd — no cross-env drift in the contract), BH14 (cosmetic defensive branches), EC2 (cosmetic diagnostic in a rare TOCTOU race; outcome stays error/exit 2), EC3 (sanitizing the DEP-code segment would REGRESS the fail-loud on a newline-bearing code from `engine-output-unrecognized` to a quiet indeterminate — current asymmetry is intentional).

## Auto Run Result

Status: done

**Change:** Wired `deptry` in as the first real engine (Story 1.3). deptry runs through the new load-bearing `_engine_env()` subprocess seam (system-temp `-o` output, `NO_COLOR=1`, `stdin=DEVNULL`, argv-only, bounded timeout, `utf-8-sig` decode, typed `ErrorRecord`s, temp cleanup on both paths). New `hygiene.py` parses DEP001–005 into `hygiene:<code>:<subject>` findings and owns the default hygiene→status table (DEP001 → policy-violation; DEP002/3/4/5 → warn; unknown code → indeterminate). `DefaultPolicy` routes hygiene-axis findings through that table (replacing the 1.2 indeterminate backstop, tighten-only; C0 preserved — a finding-carrying report never composes `clean`); `report.assemble_report` merges real per-axis hygiene coverage. DEP005 empirically confirmed = **stdlib**, not the architecture's "unused-dev" label.

**Files changed:**
- `engines.py` — `_engine_env()` seam + `DeptryEngine`; registry `[NullEngine, DeptryEngine]`.
- `hygiene.py` (new) — deptry-JSON parse, per-code join, default policy table, `unparseable_rate` ratchet.
- `interfaces.py` — `DefaultPolicy` hygiene-axis routing.
- `report.py` — per-axis engine-coverage merge (`deps_assessed`).
- `cli.py` — `manifests_parsed>0` engine gate + thread `engine_results` into the report.
- fixtures — `clean/` now imports its declared deps; new `deptry_{missing,unused,stdlib,ignore}/`; `sentinel/` gains `[tool.deptry] ignore=["DEP002"]`.
- tests — new `test_hygiene.py` + `test_engine_env_deptry.py`; extended conformance harness; updated 2 prior unit tests for real-engine behavior.

**Review findings (Blind Hunter + Edge Case Hunter, Opus):** 17 → 3 patched (low), 5 deferred, 9 rejected; intent_gap 0, bad_spec 0. Both reviewers independently confirmed the never-false-green (C0) property holds through the new hygiene routing.

**Verification:** `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` → **424 passed** (re-confirmed after the review patches). Frozen 1.1 artifacts (`models.py`/`inventory.py`/`verdict.py`/`data/*.json`) and all manifests (`pixi.toml`/`pixi.lock`/`pyproject.toml`) unchanged; sole-ownership / no-execution / socket-deny meta-guards green; twice-run byte-identical; false-green = 0.

**Residual risks:** deptry's env-coupled classification (D1) and the `deps_assessed=inventory.count` coverage proxy (D2) are honesty limitations bounded to later stories (1.7 no-scan guard / 1.9 discovery) and do NOT affect the 1.3 exit-code gate (driven by findings/status, not coverage). Coverage over-claim on fully-`exclude`d source can read as `clean`/exit 0 — the same class as 1.2's no-scan gap, explicitly owned by Story 1.7.
