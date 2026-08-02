---
title: "Test Architecture — pyforge-steward"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "4 epics (Keys/Deploy/Provision/Budget), 18 stories — 3 done (Epic 1), 15 pending; pytest, 3 established test tiers (unit/conformance/meta)"
target_coverage: "100% of DONE stories mapped to real, currently-green test files; PENDING stories carry a planned test-level note only — no file is claimed until it exists"
---

# Test Architecture — PyForge Steward

## Executive Summary

This document was authored **2026-08-02** to replace a fabricated placeholder. The prior
`test-architecture.md` (78 lines) was generic boilerplate — a template with `Target Stories: TBD`
on every row, no reference to any real story or file, produced in a bulk commit that also
contained a false migration note and other fabricated content elsewhere in the repo. All of it was
discovered and remediated this session. This replacement contains only real, verified facts:
every DONE story below is mapped to an actual test file that exists in
`src/shared/packages/pyforge-steward/tests/` and passes today (56/56 tests green, confirmed via
`pixi run -e pyforge-steward pyforge-steward-test` on 2026-08-02). Every PENDING story is marked
plainly as not yet built, with a planned test level noted — no invented file name appears anywhere
in this document.

**Steward is 17% code-complete: 3 of 18 stories done** (all three in Epic 1). Epics 2 (Deploy), 3
(Provision), and 4 (Budget) have zero implementation — no `deploy.py`, `provision.py`, or
`budget.py` exists in the package yet; `cli.py`'s dispatcher declares their subcommand names but
routes them to `NullDuty` stubs.

**Why Epic 1's test coverage is the highest-stakes in this document.** Epic 1 ("Keys — Credential
Lifecycle") exists because this repo has already paid for its absence twice, on dated incidents:

1. **The JFrog API key leak (surfaced 2026-05-10).** `.claude/skills/conda-forge-expert/scripts/_http.py`'s
   `make_request` attached JFrog auth headers (`X-JFrog-Art-Api` / HTTP Basic from
   `JFROG_USERNAME`+`JFROG_PASSWORD`) to **every outbound request, unconditionally, whenever those
   env vars were set** — with no check against the request's destination host. Any resolver that
   fell through to a public host (`conda.anaconda.org`, `raw.githubusercontent.com`, PyPI, S3)
   leaked the credential into that host's server logs. Partially mitigated in v8.14.0
   (2026-06-12, a per-call-site `skip_auth` opt-out); a durable host-scoped gate followed.
2. **The Anthropic API key leak (discovered/purged 2026-07-24/25).** A real `sk-ant-` key was
   committed in plaintext to `docs/specs/gists/conda-forge-notes/conda-forge-notes.txt`, requiring
   a `git-filter-repo` history purge across every branch that carried it, a force-push of `origin/main`,
   and rotation of the key at console.anthropic.com — history rewrite alone does not un-leak a key
   already reachable on GitHub.

Both incidents are the same defect shape: a credential attached without regard to where it was
going, or sat committed where it should never have lived. Epic 1's stories 1.2 and 1.3 are the
direct fix, and their test files are the only automated guarantee in this repo that the pattern
cannot recur silently:

- `conformance/test_keys_host_scoping.py` (14 tests) — proves a credential's headers **never**
  attach to a URL outside its declared host allowlist, even with the credential env var set. This
  is the JFrog-leak regression test, by name.
- `conformance/test_keys_encrypt_decrypt.py` (9 tests) + `conformance/test_keys_plaintext_secret_scan.py`
  (10 tests) — prove secrets round-trip correctly through `age` encryption and that a
  plausibly-plaintext secret (including an Anthropic-key-shaped string) committed to a directory is
  flagged, not silently missed. This is the Anthropic-key-leak regression coverage.
- `conformance/test_keys_audit_drift.py` (4 tests) — proves the drift-detection primitive that will
  back `steward keys audit --drift` (Story 1.6, still pending) both flags the pre-fix
  unconditional-injection shape and reports clean against the real, already-fixed `_http.py`.

If any of these four files regresses, it means one of the two incidents that already happened to
this repo can happen a third time undetected. No other test file in this package carries that
weight.

---

## Test Strategy by Epic

### Epic 1: Keys — Credential Lifecycle (7 stories — 3 done, 4 pending)

**Scope**: Credential lifecycle CLI (`steward keys ...`) plus Story 1.1's shared packaging
scaffold (the `Duty` protocol, the exit-code-owning `cli.py` dispatcher) that Epics 2–4 reuse
unchanged. Governed by AD-1, AD-2, AD-3, AD-7, AD-8, AD-9.

| Story | Title | Status | Test coverage | Level |
|-------|-------|--------|----------------|-------|
| **1.1** | Steward exists as an installable CLI | ✅ DONE | `unit/test_cli.py` (11 tests — dispatcher, `--version`/`--help`, exit-code ownership AD-8, `KeyboardInterrupt`→130, crash→70) + `meta/test_invariants.py` (3 tests — implicit-namespace PEP 420, no click/typer dependency, no `sys.exit()` outside `cli.py`) + `conformance/test_duty_protocol.py` (5 tests — `Duty`/`DutyResult`/`NullDuty` structural conformance, AD-7) | Unit + Conformance + Meta |
| **1.2** | Credentials never attach outside their declared host, and the JFrog leak can never recur silently | ✅ DONE | `conformance/test_keys_host_scoping.py` (14 tests — FR-7 regression: out-of-allowlist host returns `{}` even with env var set; port/IPv6/subdomain-lookalike edge cases) + `conformance/test_keys_audit_drift.py` (4 tests — the FR-4 drift-detection **primitive** only; see investigation note below) | Conformance |
| **1.3** | Secrets Steward stores live encrypted in Git, never as plaintext | ✅ DONE | `conformance/test_keys_encrypt_decrypt.py` (9 tests — `age` round-trip, wrong-identity failure, CLI dispatch, `-` stdio-sentinel rejection) + `conformance/test_keys_plaintext_secret_scan.py` (10 tests — Anthropic-key/age-identity/PEM patterns, UTF-16 evasion, dangling-symlink/unreadable-dir fail-closed behavior) | Conformance |
| **1.4** | Rotating a key never breaks what already trusted it | ⏳ PENDING — not yet built | No file exists. Planned: a conformance test extending Story 1.3's `age` fixtures — generate an identity, encrypt, rotate, assert old identity now fails to decrypt and new identity succeeds; assert no cron/scheduler path exists (rotation is on-demand only, per the PRD's risk-triggered decision) | Planned: Conformance |
| **1.5** | The operator can see every credential Steward knows about, never a secret value | ⏳ PENDING — not yet built | No file exists. Planned: a conformance test for `steward keys list` (identity/scope/last-rotated/provenance fields) plus a dedicated `meta/` invariant test for NFR-7 — no flag combination may ever print a raw secret value, mirroring `pyforge-warden`'s own invariant-test convention | Planned: Conformance + Meta |
| **1.6** | The operator can ask "is anything host-unscoped right now?" and get a real answer | ⏳ PENDING — not yet built | No new primitive is needed — `keys.py`'s `scan_file`/`scan_source` (proven by the existing `test_keys_audit_drift.py`) and `scan_directory_for_secrets` (proven by `test_keys_plaintext_secret_scan.py`) already exist. What's missing and untested is the **CLI verb itself**: `steward keys audit --drift` is not yet wired into `cli.py`'s `_add_keys_subparsers`, and the `-dogfood` pixi task does not yet run it against this repo. Planned: a conformance test exercising `steward keys audit --drift` end-to-end through `main()`, plus a dogfood-task assertion that it exits 0 against the current repo | Planned: Conformance + dogfood |
| **1.7** | Retiring a credential leaves a record, not a silent gap | ⏳ PENDING — not yet built | No file exists. Planned: a conformance test for `steward keys revoke --scope <name>` — inventory entry marked retired, remediation guidance printed per provenance; plus an import-scan assertion (mirrors `test_invariants.py`'s AST-based pattern) that no third-party API client import exists in the revoke path | Planned: Conformance |

**Investigation note — `test_duty_protocol.py` and `test_keys_audit_drift.py`.** Both names could
plausibly suggest they belong to a later, still-pending story (1.5 "inventory"/1.6 "audit" both
sound adjacent). Reading the actual file content and docstrings resolves this:

- **`test_duty_protocol.py` is Story 1.1's, not a later story's.** Its docstring states it verifies
  "FR-level behavioural contract: anything Steward dispatches IS a Duty (AD-7)." It tests
  `interfaces.Duty`/`DutyResult`/`NullDuty` and `cli.resolve_duty` — the shared scaffold
  `epics.md` explicitly assigns to Story 1.1 ("Shared `Duty` protocol + exit-code sole ownership
  ... established once, in Epic 1 Story 1.1, and reused unchanged by Epics 2-4"). It is
  cross-cutting by design: it parametrizes over `DUTIES = ("keys", "deploy", "provision", "budget")`,
  so it already asserts the protocol contract for duties that don't have real implementations yet
  (they resolve to `NullDuty` and still satisfy `Duty` structurally). This is Story 1.1 test
  coverage, not scaffold left over for a future story.
- **`test_keys_audit_drift.py` is Story 1.2's, not Story 1.6's — by the story spec's own words.**
  The test file's docstring is explicit: *"Drift-detection primitive (FR-4) — proven both ways
  (Story 1.2)... Story 1.6 wires this into a `steward keys audit --drift` verb; this story only
  proves the primitive itself."* Story 1.2's own acceptance criteria in `epics.md` carve out
  exactly this split: *"steward keys audit --drift-equivalent logic (this story's slice: the
  underlying detection primitive Story 1.6 later exposes as a full CLI verb)."* Confirmed against
  `cli.py`: `_add_keys_subparsers` wires only `encrypt`/`decrypt` today — there is no `audit`
  subparser, and `keys.py`'s own module docstring says so directly ("There is still no `steward
  keys audit` verb — Story 1.6 exposes both this module's findings ... through one CLI verb").
  So the primitive (`scan_file`/`scan_source`/`DriftFinding`) is real, tested, and done as part of
  Story 1.2; the CLI surface that would let an operator actually run it is Story 1.6's still-open
  work, and Story 1.6 is correctly marked pending above.

---

### Epic 2: Deploy — Reconciled Dashboard Publishing (4 stories — 0 done, 4 pending)

**Scope**: `steward deploy dashboard` — build/reconcile/dry-run/status over the existing
`dashboard-gen` pixi task. Governed by AD-1, AD-4. **No code exists** — `deploy.py` is not present
in `src/pyforge/steward/`; `resolve_duty("deploy")` returns `NullDuty`.

| Story | Title | Status | Planned test coverage | Level |
|-------|-------|--------|------------------------|-------|
| **2.1** | The dashboard builds through Steward, not a bare pixi task | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward deploy dashboard --build` invokes the exact `dashboard-gen` pixi task (subprocess boundary mocked or run for real against a scratch `docs/dashboard/`), and that a non-zero task exit surfaces as a clear Steward-level failure | Planned: Conformance |
| **2.2** | Nothing happens unless something actually changed | ⏳ PENDING — not yet built | Planned: a conformance test asserting **zero commits** when a fresh build matches the committed tree (run twice, `git log` unchanged), and **exactly one** commit containing only the changed files when a real diff exists — this is the FR-9 zero-commit-on-no-diff property and needs a real or fixture git repo, not a mock | Planned: Conformance |
| **2.3** | The operator can see what would change before it changes | ⏳ PENDING — not yet built | Planned: a conformance test asserting `--dry-run` prints the diff and leaves `git log`/`git status` byte-for-byte unchanged, both for a real pending diff and for a clean tree | Planned: Conformance |
| **2.4** | The operator can ask "when did the dashboard last actually deploy?" | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward deploy status` reads the last deploy commit's SHA/timestamp from Git history (no separate state file, per FR-11) and reports clearly — not a crash, not a misleading empty result — when no prior deploy commit exists | Planned: Conformance |

---

### Epic 3: Provision — Environment & Runner Access (4 stories — 0 done, 4 pending)

**Scope**: `steward provision` — thin CLI face over `pixi.toml`'s `[environments]` table and
`scripts/bmad-loop-worktree`. Governed by AD-1, AD-5. **No code exists** — `provision.py` is not
present; `resolve_duty("provision")` returns `NullDuty`.

| Story | Title | Status | Planned test coverage | Level |
|-------|-------|--------|------------------------|-------|
| **3.1** | Any named pixi environment materializes with one command | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward provision --env <name>` shells out to `pixi install -e <name>` for a valid name, and reports a clear error (listing valid names) for an invalid one rather than passing it through to raw pixi output; this story's own AC also names `steward provision --env pyforge-steward` as a dogfooding target | Planned: Conformance + dogfood |
| **3.2** | A bmad-loop runner and its environment materialize together | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward provision --runner bmad-loop --env <name>` invokes `scripts/bmad-loop-worktree` as a subprocess and materializes the named environment inside the resulting worktree, and that a script failure surfaces as a clear error with no orphaned worktree left unreported | Planned: Conformance |
| **3.3** | The operator can see every environment that exists, before picking one | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward provision --list` (and `--json`) enumerates every entry in `pixi.toml`'s `[environments]` table with its composing features, read-only | Planned: Conformance |
| **3.4** | The environment.yaml sync gate is one command away | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward provision --verify` reports clean when `environment.yaml` matches `pixi.toml` and reports drift (non-zero exit) when it doesn't, wrapping the existing sync-gate check rather than reimplementing the comparison | Planned: Conformance |

---

### Epic 4: Budget — Declared Resource Ceilings (3 stories — 0 done, 3 pending)

**Scope**: `steward budget` — declare/show/check a machine-readable ceiling, honestly. Governed by
AD-1, AD-6. **No code exists** — `budget.py` is not present; `resolve_duty("budget")` returns
`NullDuty`.

| Story | Title | Status | Planned test coverage | Level |
|-------|-------|--------|------------------------|-------|
| **4.1** | A ceiling can be declared, machine-readably | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward budget set --cap 1500usd/month` writes a stable, documented schema to `.steward/budget.yaml`, and that a malformed cap value reports a usage error without writing a corrupt entry | Planned: Conformance |
| **4.2** | The declared ceiling is one command away | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward budget show` (and `--json`) prints a previously declared ceiling, and reports clearly (not a crash, not a misleading zero) when none has been declared | Planned: Conformance |
| **4.3** | Asking "am I under budget?" never lies | ⏳ PENDING — not yet built | Planned: a conformance test asserting `steward budget check` always reports "no metered spend source configured" via a distinct, documented exit code regardless of whether a ceiling is declared; plus a `meta/`-style import-scan assertion that no cloud-cost-SDK (Kubecost/OpenCost/Infracost-class) import exists anywhere in `budget.py` — the honest-stub property is structural, not just behavioral | Planned: Conformance + Meta |

---

## Test Coverage Summary

| Level | Real files | Real tests | Stories covered | Status |
|-------|-----------|-----------|------------------|--------|
| **Unit** | 1 (`unit/test_cli.py`) | 11 | 1.1 | ✅ green |
| **Conformance** | 5 (`conformance/*.py`) | 42 | 1.1, 1.2, 1.3 | ✅ green |
| **Meta** | 1 (`meta/test_invariants.py`) | 3 | 1.1 (cross-cutting) | ✅ green |
| **Total (real, DONE stories)** | **7** | **56** | **3 of 18 (17%)** | ✅ all green (`pixi run -e pyforge-steward pyforge-steward-test`, 2026-08-02) |
| **E2E** | 0 | 0 | none | Not applicable yet — no surface exists to exercise end-to-end (deploy/provision/budget are unbuilt; `keys` has no multi-step external-system flow yet) |

**Real test inventory** (path relative to `src/shared/packages/pyforge-steward/tests/`):

| File | Tests | Story | What it proves |
|------|------:|-------|-----------------|
| `unit/test_cli.py` | 11 | 1.1 | Dispatcher: `--version`, `--help` lists all 4 duties, each duty dispatches, exit-code ownership (AD-8: `EXIT_OK`/`EXIT_FAILED`/`EXIT_INTERRUPTED`=130/`EXIT_INTERNAL`=70), crash never returns bare `1` |
| `meta/test_invariants.py` | 3 | 1.1 | PEP 420 implicit namespace (no `__init__.py` shadowing sibling stations), no click/typer dependency, no `sys.exit()` outside `cli.py` (AST-verified, not string-matched) |
| `conformance/test_duty_protocol.py` | 5 | 1.1 | `NullDuty`/`KeysDuty` structurally satisfy `Duty` (AD-7), every declared duty resolves to a conforming implementation, `DutyResult` is frozen, a non-conforming object is correctly rejected |
| `conformance/test_keys_host_scoping.py` | 14 | 1.2 | FR-7 regression: credential headers never attach outside the declared host allowlist (subdomain/suffix lookalikes, IPv6, port-qualified, scheme-less URLs all fail closed) |
| `conformance/test_keys_audit_drift.py` | 4 | 1.2 | FR-4 primitive: `scan_file`/`scan_source` flag the pre-fix unconditional-injection shape and report clean against the real, fixed `_http.py`; PEP 263 encoding cookies honored |
| `conformance/test_keys_encrypt_decrypt.py` | 9 | 1.3 | FR-2: `age` encrypt/decrypt round-trips exactly, wrong identity fails loudly, CLI dispatch (`main(["keys", "encrypt", ...])`) round-trips, `-` stdio sentinel rejected |
| `conformance/test_keys_plaintext_secret_scan.py` | 10 | 1.3 | Plaintext-secret scan: Anthropic-key/age-identity/PEM patterns detected, UTF-16-evasion resistant, fails loudly (not silently-clean) on unreadable dirs/dangling symlinks |

---

## Framework & Tooling

**Pytest** only — no Playwright, no browser/E2E harness. Steward is a CLI-only tool for a single
operator (PRD §2.2); there is no UX surface to drive with browser automation, unlike Marshal's
dashboard-facing E2E suite.

**Test tiers** (established in Story 1.1, per `epics.md`'s "Additional Requirements — Test-tier
layout"):
- `tests/unit/` — pure logic, no external process (`test_cli.py`)
- `tests/conformance/` — FR-level behavioral contracts, including regression tests for named
  incidents (`test_keys_*.py`, `test_duty_protocol.py`)
- `tests/meta/` — invariants that fail silently if unpinned (`test_invariants.py`)

**Real dependencies exercised, not mocked**: `age-keygen`/`age` (Story 1.3's tests generate real
identities and shell out to the real binary — no crypto is mocked), and `_http.py`'s
`auth_headers_for` (Story 1.2's tests import and call the real, already-fixed module via
`keys.locate_http_module()`, not a stub). This matches AD-1/AD-2's "delegate, never reimplement"
constraint: if there is nothing to reimplement, there is nothing to fake in a test either.

**Run command**: `pixi run -e pyforge-steward pyforge-steward-test` (`pytest
src/shared/packages/pyforge-steward/tests -q`) — currently 56 passed, 0 failed, 0 skipped
(2026-08-02; two `skipif` guards exist for root/Windows-only edge cases in the plaintext-secret
scan tests and did not trigger in this run).

**Coverage tooling**: not yet configured (no `pytest-cov` invocation wired into the
`pyforge-steward-test` task). Not a gap for a 3-of-18-story package — worth adding once Epic 2
lands and the surface is large enough for a percentage threshold to mean something.

---

## Readiness Checklist

- [x] All 18 stories enumerated with real status (3 done, 15 pending) — no `TBD` anywhere
- [x] All 3 DONE stories mapped to real, currently-passing test files (verified by running the suite, not by inspection alone)
- [x] `test_duty_protocol.py` and `test_keys_audit_drift.py` investigated and attributed by reading actual file content/docstrings, not by name-guessing
- [x] All 15 PENDING stories carry a planned test-level note, zero invented file names
- [x] Epic 1's incident-driven stakes stated explicitly (JFrog leak 2026-05-10, Anthropic key leak 2026-07-24/25)
- [ ] Epic 2 (Deploy) test scaffolding — blocked on Story 2.1 landing
- [ ] Epic 3 (Provision) test scaffolding — blocked on Story 3.1 landing
- [ ] Epic 4 (Budget) test scaffolding — blocked on Story 4.1 landing
- [ ] Coverage-percentage tooling (`pytest-cov`) — deferred until the surface is large enough to threshold meaningfully
- [ ] E2E harness — not applicable until a multi-step external-system flow exists to exercise (earliest candidate: Epic 2's dashboard build→diff→push→status chain)

---

**Status**: DRAFT — accurate as of 3/18 stories built; re-run this document's "Real test inventory"
section after every story that lands (do not batch the update — a stale mapping here is exactly
the failure mode this replacement exists to fix).

**Last updated**: 2026-08-02
