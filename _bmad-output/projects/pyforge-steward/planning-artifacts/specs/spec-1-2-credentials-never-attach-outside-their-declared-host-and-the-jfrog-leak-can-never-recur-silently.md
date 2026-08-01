<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.2: Credentials never attach outside their declared host, and the JFrog leak can never recur silently'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
final_revision: '7aa2aa008883b29515c53c3ab2ea8ea5a7f2ce46'
---

<intent-contract>

## Intent

**Problem:** `_http.py`'s `auth_headers_for` attaches credential headers (e.g. `JFROG_API_KEY`) to any outbound request unless the *caller* opts out per call site (`skip_auth=True`); there is no reusable primitive that gates attachment by an explicit, declared host allowlist, and nothing would catch a regression back to the pre-fix unconditional-injection shape.

**Approach:** Add `steward.keys`'s host-scoped resolver — `resolve_headers(credential, url)` — which computes whether `url`'s host is inside a credential's declared allowlist and passes that decision through as `_http.py`'s existing `skip_auth` parameter (AD-2: delegate, never reimplement). Add the drift-detection primitive (`scan_source`/`scan_file`) that AST-scans a Python source file for the historical unconditional-injection shape. Both land in `keys.py` — the architecture's single duty-adapter-module design for Epic 1 — with no CLI verb wired yet (Story 1.6 exposes `steward keys audit --drift`).

## Boundaries & Constraints

**Always:**
- `resolve_headers` delegates entirely to `_http.py`'s `auth_headers_for(url, skip_auth=...)` — it decides only host membership, never builds its own request/header logic (AD-1, AD-2).
- Import `_http.py` the same way every existing conda-forge-expert script does (locate its directory, insert onto `sys.path`, `from _http import auth_headers_for`) — no vendoring or copying its logic.
- The drift primitive lives in the same `keys.py` module as the resolver (architecture's single-file duty-adapter convention for Epic 1) — no new subpackage.
- A `tests/conformance/` test exercises the resolver directly (empty headers outside the allowlist, correct headers inside it) so it fails loudly if the host gate is ever removed or bypassed — this is FR-7's regression test.
- The drift primitive is proven both ways: a fixture reproducing the pre-fix unconditional-injection shape returns a finding; the real, already-fixed `.claude/skills/conda-forge-expert/scripts/_http.py` returns clean.

**Block If:** none — self-contained library code, no ambiguous external decision points.

**Never:**
- No `age` encryption/rotation/inventory/revoke work — that's Stories 1.3–1.7.
- No modification to `_http.py` itself — it is already fixed; this story only builds Steward's consumer-side wrapper and detector.
- No general-purpose static-analysis framework — the detector targets this one defect shape, not a pluggable rule engine.
- No real secret values anywhere in the fixture — synthetic placeholder strings only.
- No CLI wiring — `cli.py`'s `resolve_duty("keys")` keeps returning `NullDuty` this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| In-allowlist host | `credential.hosts=("artifactory.example.com",)`, url on that host, `JFROG_API_KEY` set | Returns `{"X-JFrog-Art-Api": <value>}` | No error expected |
| Out-of-allowlist host | Same credential, url on a different host | Returns `{}` | No error expected |
| No credential env var set | In-allowlist url, no matching env var set | Returns `{}` (nothing to attach) | No error expected |
| Fixture: ungated attachment | `scan_file(fixture_path)` | Returns exactly one `DriftFinding` naming the function + line | No error expected |
| Real, fixed `_http.py` | `scan_file(real_http_py_path)` | Returns `[]` | No error expected |
| Malformed source | `scan_source("not valid python(")` | Raises `SyntaxError` | Propagates — not swallowed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- NEW: host-scoped resolver + drift-detection primitive (this story's entire surface)
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_host_scoping.py` -- NEW: FR-7 regression test + resolver behavior
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_audit_drift.py` -- NEW: drift primitive vs fixture + real `_http.py`
- `src/shared/packages/pyforge-steward/tests/conformance/fixtures/ungated_jfrog_auth.py` -- NEW: synthetic pre-fix-shape fixture (scanned only, never imported)
- `.claude/skills/conda-forge-expert/scripts/_http.py` -- READ-ONLY reference: `auth_headers_for(url, skip_auth=...)` is the delegate target
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- READ-ONLY reference: confirms `keys` duty is untouched this story (still `NullDuty`)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/steward/keys.py` -- add `locate_http_module()` (walks up from `__file__` for the `.claude/skills/conda-forge-expert/scripts/_http.py` marker), the `sys.path` bridge that imports `auth_headers_for`, `HostScopedCredential`, `resolve_headers()`, `DriftFinding`, `scan_source()`/`scan_file()`, and their private AST helpers -- builds the FR-1/FR-4/FR-7 slice this story owns
- [x] `tests/conformance/fixtures/ungated_jfrog_auth.py` -- add a small synthetic function reproducing the pre-`skip_auth` `auth_headers_for` shape (unconditional env-var-to-header attachment, no gate) -- gives the drift primitive a positive fixture without touching real credentials or the real, already-fixed `_http.py`
- [x] `tests/conformance/test_keys_host_scoping.py` -- cover the I/O matrix's resolver rows as the FR-7 regression test (out-of-allowlist → `{}`, in-allowlist → correct header, no-env-var → `{}`) -- this is the "fails loudly if gating is removed" test
- [x] `tests/conformance/test_keys_audit_drift.py` -- scan the fixture (expect one finding) and the real `_http.py` (expect clean), plus the malformed-source `SyntaxError` case -- proves the detection primitive both ways

**Acceptance Criteria:**
- Given a `HostScopedCredential` with an explicit host allowlist and a URL outside it, when `resolve_headers` is called, then it returns `{}` with no credential-bearing header, even when the matching env var is set.
- Given the same credential and a URL inside its allowlist, when `resolve_headers` is called, then it returns the header `_http.py`'s `auth_headers_for` would produce for that host.
- Given the fixture reproducing the pre-fix unconditional-injection shape, when `scan_file` runs against it, then it returns exactly one `DriftFinding` naming the offending function and line.
- Given the actual current `.claude/skills/conda-forge-expert/scripts/_http.py`, when `scan_file` runs against it, then it returns `[]`.
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when the suite runs, then all of Story 1.1's existing tests plus this story's new tests pass, and `steward --help`/`--version` behavior is unchanged (no CLI surface touched).

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 3 (medium 2, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` `HostScopedCredential` accepted an empty `hosts` tuple or a bare string (silently iterated per-character, matching nothing) with no diagnostic — added `__post_init__` validation raising `TypeError`/`ValueError`, plus regression tests.
  - `[medium]` `[patch]` Host comparison in `resolve_headers` didn't strip a port suffix or trailing DNS root dot, so a plausible `hosts` entry like `"artifactory.example.com:8081"` would silently never match and permanently disable the credential — added `_canonical_host()` normalization applied to both the URL's host and every `credential.hosts` entry, plus a regression test.
  - `[low]` `[patch]` `scan_source`'s docstring claimed it looks for a "header-dict assignment" when the implementation actually matches any `os.environ`-sourced value assigned into any subscripted target — tightened the docstring to describe the actual (deliberately broader, single-defect-shape) match surface and its scope boundary.

### 2026-07-30 — Review pass (follow-up on `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 2, low 2)
- defer: 3 (medium 2, low 1)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `_canonical_host`'s `rsplit(":", 1)` corrupted bare IPv6 literals — `"2001:db8::1"` and `"2001:db8::2"` both canonicalized to `"2001:db8:"`, so a credential declared for one IPv6 host attached to a *different* IPv6 host (confirmed by execution) — rewrote canonicalization to strip a port only from bracketed (`[::1]:8081`) or single-colon (`host:port`) forms; bare multi-colon hosts are addresses and are kept whole. IPv6 regression tests added.
  - `[medium]` `[patch]` `__post_init__` accepted hosts entries that canonicalize to an empty hostname (`""`, `"."`, `":8081"`) — an empty canonical entry matched hostname-less strings and attached credentials to garbage URLs (confirmed by execution) — and URL-shaped entries (`"https://…"`, canonicalizing to `"https"`) that silently never match; both now raise `ValueError` at construction, with regression tests.
  - `[low]` `[patch]` `HostScopedCredential`'s docstring implied per-credential scoping the primitive doesn't provide (in-allowlist URLs receive whatever `_http.py`'s host-blind chain resolves first, e.g. the ambient JFrog key on an allowlisted `github.com`) — added an explicit scope note (the gate decides *whether* ambient auth attaches, not *which* credential) and documented exact-match/no-subdomain semantics.
  - `[low]` `[patch]` Security-relevant matching semantics were untested — added subdomain non-match, suffix-lookalike non-match (`artifactory.example.com.evil.example`), and multi-entry allowlist regression tests.

### 2026-07-30 — Review pass (second follow-up on `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 1, low 4)
- defer: 2 (medium 2) — both found already recorded verbatim in the deferred-work ledger by the prior pass (drift-detector heuristic limits; scheme-blind `http://` attachment); per the orchestrator's "NEW entries only" constraint, no duplicate entries were appended.
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `_canonical_host` treated ANY single-colon suffix as a port — a mistyped entry like `"https:artifactory.example.com"` canonicalized to `"https"`, and `"evil.com:artifactory.example.com"` to `"evil.com"`: a hostname the author never wrote, in the allowlist controlling credential release (confirmed by execution) — port stripping is now numeric-only, and `__post_init__` rejects single-colon entries whose suffix is not a numeric port. Regression tests added.
  - `[low]` `[patch]` `__post_init__` accepted entries containing characters that can never appear in a parsed URL hostname (`@`, `?`, `#`, `*`, whitespace) — a silently-dead credential, the failure mode the validation exists to prevent (confirmed by execution) — now rejected at construction, with regression tests.
  - `[low]` `[patch]` `resolve_headers`'s behavior on unparseable URLs was unpinned — a scheme-less URL silently fails closed to `{}` (hostname parses as `None`) while a malformed bracketed-IPv6 URL raises `ValueError` from `urlparse` (both confirmed by execution) — documented in the docstring and pinned with tests; no behavior change.
  - `[low]` `[patch]` The URL-side port direction (`https://artifactory.example.com:8081/x` against a portless entry — the direction real Artifactory deployments on the default 8081 actually hit) was untested; regression test added (behavior was already correct).
  - `[low]` `[patch]` `scan_file` hard-coded UTF-8, so a PEP 263 encoding-cookie source file raised `UnicodeDecodeError` instead of being scanned — now opened with `tokenize.open`, with a test proving a latin-1 file is scanned and its planted finding detected.

## Design Notes

The drift primitive's "gated" heuristic: within a function body, a top-level `if <cond>: return ...` counts as a **scope gate** only when `<cond>` does *not* itself just re-check the secret env var's own presence (a presence check like `if os.environ.get("JFROG_API_KEY"):` is not a scope gate). Once a scope gate is seen, later statements in that function are not flagged. This is exactly what distinguishes the current `auth_headers_for` (`if skip_auth: return {}` gates everything below it) from the pre-fix shape (no such gate exists, so the first unconditional env-var→header assignment is flagged).

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (19 existing Story 1.1 tests + this story's new tests)

## Auto Run Result

**Run 2026-07-30 (second follow-up review pass on `done` spec; commit `7aa2aa0088`).**

**Summary:** Fresh adversarial + edge-case review of the full Story 1.2 diff since baseline `e868b607`. No intent gaps, no spec defects. Five findings patched; two real-but-out-of-scope findings were confirmed already recorded verbatim in the deferred-work ledger by the prior pass, so no new ledger entries were appended (orchestrator constraint: NEW entries only); eight rejected (spec-mandated design — the `sys.path` import bridge and checkout-required location are Boundaries "Always" clauses; the single-defect-shape detector scope is a "Never" clause — or speculative).

**Files changed this pass:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — numeric-only port stripping in `_canonical_host`; `__post_init__` now rejects non-numeric single-colon suffixes and never-parseable characters (`@ ? # *`, whitespace); `resolve_headers` docstring pins unparseable-URL behavior; `scan_file` uses `tokenize.open` (PEP 263).
- `tests/conformance/test_keys_host_scoping.py` — 4 new tests: never-matching entries rejected, URL-side port match, scheme-less URL fails closed, malformed-IPv6 `ValueError` propagates.
- `tests/conformance/test_keys_audit_drift.py` — 1 new test: latin-1 PEP 263 file is scanned and its planted finding detected.

**Findings breakdown:** patch 5 (medium 1, low 4) — all applied; defer 2 (both already ledgered, no new entries); reject 8.

**Verification:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` → 37 passed (32 pre-existing + 5 new). Reviewer claims re-verified by direct execution before patching (`urlparse` ValueError on `https://[::1`, `"https:host"` → `"https"` canonicalization, `tokenize.open` cookie handling).

**Residual risks:** the drift detector remains scoped to the one historical defect shape — its evasion space (respelled env reads, unrelated early-return gates, Compare-form presence checks, non-`Assign` shapes) is documented in the deferred-work ledger for hardening in/after Story 1.6. Per-credential header selection and scheme policy are likewise ledgered for later keys stories.

**Follow-up review recommended:** false — this pass's fixes are localized validation tightening plus test/doc pinning; both follow-up passes have converged (reviewers now predominantly re-surface already-triaged or already-ledgered items).

**Manual checks (if no CLI):**
- This worktree's path exceeds the known pixi-build-python worktree-path-length panic threshold (~173 bytes; see auto-memory `project_bmad_loop_worktree_path_length_limit.md`). If `pixi run` fails with "the build backend (pixi-build-python) exited prematurely," use the documented short-detached-worktree workaround rather than treating it as a code defect. (Follow-up pass 2026-07-30: `pixi run --frozen -e pyforge-steward pyforge-steward-test` bypasses the panic entirely — the failure is at env-solve time, and `--frozen` skips the solve; safe whenever the story didn't touch `pixi.toml`.)

