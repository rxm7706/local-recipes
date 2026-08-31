---
title: 'Export gated server-side (Epic 9 Story 9.4, pyforge-steward)'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: 'cfbee8bdf1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-secure-live-dashboards-2026-08-09/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pyforge.steward.dashboard` (Story 9.1) has identity/role extraction and the
declaration schema but no export gate at all: any caller who reaches an adopter's export
endpoint directly (bypassing the UI entirely) gets the data, with no server-side role check,
no record of the attempt, and no way to deliver the file encrypted.

**Approach:** Add `dashboard/export.py` — an `ExportPolicy` declaration (allowed roles, an
optional webhook URL, an optional `age` encryption recipient), one `authorize_export()` gate an
adopter's export view calls that raises on an unauthorized role while logging a security event
and best-effort POSTing it to the configured webhook, and `maybe_encrypt_export()` which
encrypts the produced artifact via Story 1.3's existing `keys.encrypt_file()` when a recipient
is declared.

## Boundaries & Constraints

**Always:**
- `export.py` lives under `dashboard/` and stays django-free like `middleware.py`/`declarations.py`
  (no `django`/`channels` import), so export gating works without the `[dashboard]` extra.
- `authorize_export()` is the only place the decision is made; an adopter's UI hiding the export
  control is never sufficient on its own (standing epic constraint).
- Every refusal logs a security event via `logging.getLogger("pyforge.steward.dashboard.security")`
  and, if `policy.webhook_url` is set, attempts one best-effort HTTP POST — a webhook failure is
  caught and logged but never suppresses or delays the raised refusal.
- Encryption reuses `keys.encrypt_file()` (Story 1.3, shells to the real `age` binary) — no new
  crypto dependency.
- `ExportPolicy` fields are validated at construction, mirroring `AccessDeclaration`'s exact style
  (type + emptiness + no-padding checks naming the offending field).

**Block If:** none identified — CAP-5 has no undecided cross-cutting question this story's own
scope depends on.

**Never:**
- Build Story 9.3's durable audit-trail model. 9.4 depends only on S-9.1 (epics.md), and 9.3 is
  still backlog, so "recorded as a security event" here is a `logging` call, not a DB write — the
  natural integration point once 9.3 lands, not a substitute for it.
- Add a `steward deploy` CLI verb for webhook/export wiring verification. The architecture map
  reads `CAP-5 | library (refusal) + subcommand (alerting)`, but `deploy.py` importing anything
  from `dashboard/` — even a django-free module — is exactly what
  `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` forbids: no file outside
  `dashboard/` may import `pyforge.steward.dashboard` at all. Read "subcommand (alerting)" as
  belonging to Story 9.5's
  deployment-perimeter surface, which is where a live wiring-verification CLI check can exist
  without violating that invariant; 9.4 ships the in-process refusal + alert dispatch this story's
  own Given/When/Then names, in full.
- Add `requests` or any third-party HTTP client — the webhook POST uses stdlib `urllib.request`.
- Cross-validate `ExportPolicy.allowed_roles` against `AccessDeclaration.roles` — independent
  declarations by design (9.1's reviews rejected this same coupling for `TrustedIngress`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authorized role | `role` is in `policy.allowed_roles` | `authorize_export` returns `None`; no log, no webhook call | No error expected |
| Unauthorized role | `role` not in `policy.allowed_roles` | raises `ExportUnauthorizedError`; a security-event WARNING is logged | Raised after recording |
| No identity/role (`role=None`) | caller has no resolved role | treated as unauthorized — same as above (CAP-1's degrade-to-unprivileged) | Raised after recording |
| Webhook configured, refusal occurs | `policy.webhook_url` set | one POST attempted with the event payload before the exception propagates | POST failure caught, logged, refusal still raised |
| Webhook configured, receiver unreachable/times out | network error | webhook failure logged as a secondary warning | `ExportUnauthorizedError` still raised, unaffected |
| No webhook configured | `policy.webhook_url is None` | refusal still raised + logged; no POST attempted | No error |
| `ExportPolicy.allowed_roles` empty or non-tuple | `roles=()` or `roles="viewer"` | raises at construction | `ValueError`/`TypeError` naming the field |
| `ExportPolicy.webhook_url` malformed | `"not-a-url"`, `"ftp://x"` | raises at construction | `ValueError` naming the field |
| `ExportPolicy.encryption_recipient` blank/padded | `""`, `"  key  "` | raises at construction | `ValueError` naming the field |
| `maybe_encrypt_export`, recipient declared | `policy.encryption_recipient` set | calls `keys.encrypt_file`; returns the encrypted path; ciphertext unreadable without the matching `age` identity | `subprocess.CalledProcessError` propagates unmodified |
| `maybe_encrypt_export`, no recipient | `policy.encryption_recipient is None` | returns the original path unchanged, no encryption performed | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/export.py` -- NEW: `ExportPolicy` frozen dataclass, `ExportUnauthorizedError`, `authorize_export(*, identity, role, policy, logger=None)`, `maybe_encrypt_export(path, policy, *, output)`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/__init__.py` -- MODIFY: name `export.py` among the django-free modules in the module docstring, mirroring the existing convention.
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- MODIFY: add `"export.py"` to `test_dashboard_middleware_and_declarations_stay_django_free`'s file tuple (currently `("__init__.py", "middleware.py", "declarations.py")`, line ~430).
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_export.py` -- NEW: `ExportPolicy` validation edge cases, `authorize_export` authorized/unauthorized/webhook paths (mock `urllib.request.urlopen`), `maybe_encrypt_export` round-trip using a generated `age` identity (mirrors `tests/conformance/test_keys_encrypt_decrypt.py`'s `_generate_identity` fixture pattern).

## Tasks & Acceptance

**Execution:**
- [x] `dashboard/export.py` -- implement `ExportPolicy` (allowed_roles, webhook_url, encryption_recipient) with construction-time validation mirroring `AccessDeclaration`'s style -- CAP-5's "declared, not implemented" half
- [x] `dashboard/export.py` -- implement `authorize_export()`: raise `ExportUnauthorizedError` when `role` is `None` or not in `policy.allowed_roles`; on refusal, log a WARNING via `logging.getLogger("pyforge.steward.dashboard.security")` and, if a webhook is configured, attempt one best-effort `urllib.request` POST (any failure caught and logged, never re-raised) -- CAP-5's server-side refusal + security-event recording + webhook announcement
- [x] `dashboard/export.py` -- implement `maybe_encrypt_export()` wrapping `keys.encrypt_file` -- CAP-5's optional-encryption half, reusing Story 1.3's primitive
- [x] `dashboard/__init__.py` -- extend the django-free-modules docstring list to include `export.py`
- [x] `tests/meta/test_invariants.py` -- add `export.py` to the existing django-free guard's file tuple
- [x] `tests/unit/test_dashboard_export.py` -- exercise every I/O-matrix row: `ExportPolicy` validation, `authorize_export` authorized/unauthorized/no-identity/webhook-success/webhook-failure, `maybe_encrypt_export` with/without a recipient (real `age` round-trip via a generated identity, proving the encrypted output is undecryptable without it)

**Acceptance Criteria:**
- Given an export request whose role is in the policy's allowed roles, when `authorize_export` is called, then it returns without raising and neither the logger nor the webhook is invoked.
- Given an export request whose role is absent or not allowed, when `authorize_export` is called, then it raises `ExportUnauthorizedError`, logs a security-event WARNING, and — if a webhook is configured — sends it an HTTP POST before the exception propagates.
- Given a configured webhook that is unreachable, when an unauthorized export is refused, then the webhook failure is caught and logged but `ExportUnauthorizedError` still propagates unaffected.
- Given an `ExportPolicy` constructed with an invalid `allowed_roles`, `webhook_url`, or `encryption_recipient`, when construction is attempted, then it raises immediately, naming the offending field.
- Given an export artifact and a policy declaring an `encryption_recipient`, when `maybe_encrypt_export` runs, then the returned file is real `age` ciphertext, decryptable only with the matching identity.
- Given an export artifact and a policy with no `encryption_recipient`, when `maybe_encrypt_export` runs, then the original file is returned unchanged.
- Given the whole `pyforge-steward` package, when `tests/meta/test_invariants.py` runs, then `export.py` is confirmed to import neither `django` nor `channels`.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 2, low 0)
- defer: 5: (high 1, medium 4, low 0)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[medium]` `[patch]` `ExportPolicy.webhook_url` validated only `parsed.netloc` truthiness, so `"https://@"` and `"https://:1"` (non-empty netloc, no real host) passed construction and only failed silently at POST time (Edge Case Hunter) — fixed by checking `parsed.hostname` instead, matching the codebase's established "malformed declaration fails loudly at construction" pattern; pinned by two new parametrized test cases.
  - `[medium]` `[patch]` `maybe_encrypt_export(path, policy, output=path)` had no guard against `output == path`, risking `age`'s write to `output` truncating `path` while it was still being read (Edge Case Hunter) — fixed with a construction-time-style `ValueError` before `encrypt_file` is called; pinned by a new test asserting the plaintext survives unchanged.

Deferred to `DW-FU-9-4` through `DW-FU-9-4-5` (Tier-3 `implementation-artifacts/deferred-work.md`, promoted to the tracked ledger at landing): the refusal webhook's synchronous blocking POST with no async variant or rate limit (mirrors Story 9.1's still-open `get_master_dataset()` async-blocking deferral); `maybe_encrypt_export` never deletes the plaintext source after encrypting (caller-lifecycle decision); the webhook payload is unsigned (matches the architecture spine's "webhook contract is fixed, sink adapters are a demand question" framing); `webhook_url` has no loopback/link-local/metadata-address protection (mirrors Story 9.1's open `TrustedIngress.addresses` form-validation deferral); `authorize_export` being "the only place the decision is made" is a documented convention, not code-enforced (the spec's own Design Notes already named this as Story 9.5's deployment-perimeter surface to close). All five are architecturally scoped to Story 9.5 or tied to an existing Story 9.1 precedent, none block this story's own CAP-5 scope.

Rejected as noise: an `%r`-formatted log line is not injectable (Python's `repr()` escapes embedded control characters, so the claimed log-injection finding does not reproduce); no audit trail for *successful* exports (explicitly Story 9.3's CAP-4 scope per this spec's own Never list); `role is None` handling untested against `middleware.py`'s actual scope contract (verified correct by direct code read; any drift fails closed, not open); case-sensitive role matching (already covered by Story 9.1's existing "identity/role values are verbatim, normalization is deferred to 9.3" ledger entry); no length bound on identity/role (Story 9.1 pass 3 already rejected this identical finding on the same grounds); the webhook POST's broad `except Exception` (a deliberate, documented "must never fail the refusal" design; the current fixed payload shape has no realistic serialization-failure path); no test for `identity=None` with a configured webhook (mechanical `json.dumps(None)` behavior, zero real risk); no end-to-end integration test through `middleware.py` (duplicates Story 9.1's/9.6's already-scoped end-to-end proof-suite work); the test helper's `StopIteration` on an unexpected `age-keygen` format (copied verbatim from Story 1.3's existing, already-reviewed test precedent).

## Design Notes

**Why "subcommand (alerting)" is not a new CLI verb in this story.** The architecture map's
`CAP-5 | library (refusal) + subcommand (alerting)` row reads, taken literally, as if the outbound
webhook call should live in `steward deploy`. But `deploy.py` cannot import anything from
`dashboard/` — including a django-free module — without violating the invariant
`test_no_module_outside_dashboard_imports_dashboard_django_or_channels` already enforces (AD-1:
"Steward's own CLI surface never imports them"). A live per-request webhook POST also gains nothing from an out-of-process
hop — unlike encryption, which genuinely needs the external `age` binary, an HTTP POST is ordinary
in-process work. This story's own Given/When/Then ("authorization is enforced server-side ... and
the export may be encrypted") names nothing CLI-shaped. Read literally, "subcommand (alerting)"
fits Story 9.5's deployment-perimeter surface — a `steward deploy` wiring-verification check that
an adopter's webhook config is reachable — which can exist there without this story's invariant
conflict. This is an interpretation, recorded here rather than silently assumed, so it can be
overturned in review if wrong.

**Webhook payload is intentionally minimal.** `{"event": "export_refused", "identity": ...,
"role": ..., "occurred_at": <ISO-8601 UTC>}` — no `allowed_roles` or other policy internals, for
the same reason `UntrustedIngressError` (9.1) never echoes the declared ingress list: keep an
event payload to what a receiver needs to act on, not a dump of the declaration. Unlike 9.1's
exception messages (which an untrusted caller can potentially observe via a DEBUG 500), this
payload only ever reaches the adopter's own configured webhook, so including `identity` here is
intentional — a security event with no actor is not actionable.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done`

**Implemented change.** Story 9.4 adds `pyforge.steward.dashboard.export`: `ExportPolicy`
(declared allowed roles, optional webhook URL, optional `age` encryption recipient,
construction-time validated), `authorize_export()` (the server-side export-authorization gate —
refuses an unauthorized/absent role, logs a security-event WARNING, and best-effort POSTs a
webhook announcement before raising `ExportUnauthorizedError`), and `maybe_encrypt_export()`
(wraps Story 1.3's `keys.encrypt_file` to optionally encrypt the produced export artifact).

**Files changed:**
- `src/pyforge/steward/dashboard/export.py` (NEW) — `ExportPolicy`, `ExportUnauthorizedError`, `authorize_export`, `_post_refusal_webhook`, `maybe_encrypt_export`.
- `src/pyforge/steward/dashboard/__init__.py` — docstring extended to name `export.py` among the django-free submodules.
- `tests/meta/test_invariants.py` — `export.py` added to the existing django-free import guard.
- `tests/unit/test_dashboard_export.py` (NEW) — 28 tests covering every I/O-matrix row plus the two review-pass fixes.

**Review findings breakdown:** 2 patched (both medium), 5 deferred (1 high, 4 medium — logged
to the Tier-3 deferred-work ledger as `DW-FU-9-4` through `DW-FU-9-4-5`), 9 rejected (all
low/non-issues — including one factually-incorrect log-injection claim and several already
covered by Story 9.1's existing precedent/deferrals), 0 intent_gap, 0 bad_spec.

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test` — **421 passed** (baseline before this story: 418; +3 net from the review pass's test additions).
- `pixi run -e pyforge-steward steward --version` — `steward 0.1.0`, unchanged, confirms the base package still runs without the dashboard code path invoked.

**Residual risks:**
- The five deferred items are recorded only in the gitignored Tier-3 `implementation-artifacts/deferred-work.md` — per this repo's convention, they must be promoted into the tracked `planning-artifacts/deferred-work-ledger.md` (renamed to the `DW-9-4-<n>` shape) when this story lands, or they are lost with the run worktree.
- No adopter export view exists yet to exercise `authorize_export`/`maybe_encrypt_export` end-to-end (Atlas's Vizro migration, and Stories 9.5/9.6, are where that wiring and its non-vacuous proof land) — this story's tests exercise the library functions directly, consistent with Story 9.1's/9.2's own testing shape at this stage of the epic.
- **Landing gate:** every path in this diff is outside `recipes/`, so the PR needs the `maintenance` label (per CLAUDE.md's PR CI gates). `pixi.toml` was not touched, so the `environment.yaml` sync gate does not apply.

Follow-up review recommended: `false` — both patches are small, mechanical, precedented by this
codebase's existing validation style, and each is pinned by a dedicated new test; nothing in this
pass changed a public interface, added a dependency, or touched security-sensitive logic beyond
tightening an existing check.
