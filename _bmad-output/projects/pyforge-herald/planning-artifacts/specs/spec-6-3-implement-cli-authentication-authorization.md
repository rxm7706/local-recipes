---
title: 'Implement CLI Authentication & Authorization'
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

**Problem:** AD-16 requires write operations (`herald success publish`, `herald notice author`,
a future `herald progress --update`) to verify an `operator` role before executing, with reads
staying public. No auth surface exists in Herald at all yet.

**Approach:** A new `auth.py` module -- `resolve_auth_context()` (checks `HERALD_TOKEN` env var,
then `~/.herald/config`, both AC-named sources) and `require_operator_role()` (the middleware
gate, raising `errors.OperatorAuthorizationError` -- a new `HeraldError` subclass falling through
the existing exit-code map to 1, matching the AC exactly with no new map entry). Wired into two
CLI handlers -- `herald success publish <claim-id>` and `herald notice author <name>` -- both
calling the identical gate as literally the first line of their `operation` closure, before
anything else runs (Story 6.3's own explicit scope boundary: the actual publish/author logic is
Epic 9/10's, this story only proves "authorized, would proceed").

**Explicit scope boundary (per the story's own AC):** this module answers "is there a verified
operator role?" and nothing else. It does not verify a Herald web session, does not mint or
refresh a credential (`herald auth login` is named in the remediation message but not
implemented -- same pattern as `AuthError`'s `/design-login` remediation in `errors.py`, a
pointer to an operator action outside this CLI's own scope), and real signature/session
verification against a live Herald backend is `[ASSUMPTION]`, per AD-16's own note ("confirm
with ops team").

## Boundaries & Constraints

**Always:**
- `herald success publish <claim-id>` without a verified operator role: "unauthorized: operator
  role required" on stderr, no action taken, exit 1.
- `herald success publish <claim-id>` with a verified operator role: proceeds to a stub print
  ("authorized: would publish claim ... (Epic 9 implements the actual publish)"), after an
  honored `"Continue? [Y/n]"` confirmation prompt.
- `herald progress` (no write flag): never calls `auth` at all -- reads are public per AD-16.
- No auth context resolvable at all (`HERALD_TOKEN` unset, no config file): "auth context
  missing. Configure with \`herald auth login\` or set HERALD_TOKEN env var" on stderr, exit 1.
- Every auth check (pass or refuse) is logged at INFO via `logging.getLogger("pyforge.herald.auth")`
  for the audit trail the implementation notes ask for -- the token value itself is never logged
  or retained past `resolve_auth_context`'s own parsing.
- The gate is genuinely reusable middleware, not a one-off: `herald notice author <name>` calls
  the identical `require_operator_role` function as its second caller, proving the pattern (not
  just asserted in prose).

**Block If:** N/A -- no spike, no live gate; auth resolution touches only local env/filesystem,
never the network.

**Never:**
- No trivial bypass: merely setting `HERALD_TOKEN` to any non-empty string must not grant the
  operator role. The env-var format is `<role>:<opaque-token>` (a required `:`-delimited role
  prefix) specifically so a caller with, say, a `viewer` role is distinguishable from "no auth
  context at all" -- both are AC-named scenarios with different messages, which a
  presence-only check could not produce.
- No real credential minting, refreshing, or backend session verification -- explicitly Epic
  9/10's scope (or later, per AD-16's `[ASSUMPTION]`).
- No token material in any log line or error message.

## I/O & Edge-Case Matrix

| Scenario | Auth source | Expected | Exit |
|---|---|---|---|
| No env var, no config file | none | "auth context missing..." | 1 |
| `HERALD_TOKEN=viewer:tok` | env, role=viewer | "unauthorized: operator role required" | 1 |
| `HERALD_TOKEN=operator:tok` | env, role=operator | confirm prompt -> stub "authorized" print | 0 |
| `HERALD_TOKEN=bare-token-no-colon` | malformed | treated as no auth context (not operator) | 1 |
| `~/.herald/config` `{"role": "operator"}` | file | authorized (via `config_path=` injection in tests) | 0 |
| `~/.herald/config` malformed JSON / missing `role` | file | no auth context | 1 |
| Confirmation declined | operator, answers "n" | "aborted: publish not confirmed", no publish stub printed | 0 |
| `herald progress` | (irrelevant) | never calls auth at all | 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/auth.py` -- create -- `AuthContext`,
  `resolve_auth_context`, `require_operator_role`, `confirm`, `TOKEN_ENV_VAR`,
  `DEFAULT_CONFIG_PATH`, `OPERATOR_ROLE`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit --
  `OperatorAuthorizationError` (falls through to exit 1).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `success publish`/
  `notice author` subparsers (positional `claim_id`/`name`), `_run_success_publish`,
  `_run_notice_author`.
- `src/shared/packages/pyforge-herald/tests/test_auth.py` -- create -- role resolution +
  middleware unit tests (no CLI involved).
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- create (shared with 6.1/6.2/6.5)
  -- the write-gate rows exercised through `cli.main`.
- `src/shared/packages/pyforge-herald/tests/conftest.py` -- edit -- `deny_network` (renamed in
  spirit, not in code, to "the hermetic-test fixture") now also monkeypatches
  `auth.DEFAULT_CONFIG_PATH` to a nonexistent path under `tmp_path`, mirroring the existing
  `HERALD_DESIGN_CREDENTIALS` guard -- so a CLI-level test that calls
  `auth.resolve_auth_context()` with no explicit `config_path` (exactly what the CLI handlers do)
  can never read a developer's real `~/.herald/config`.

## Design Notes

**Judgment call: the `HERALD_TOKEN` env var must encode a role, not just a token.** The AC's own
three scenarios ("without operator role" / "with operator role" / "no auth context found") need
a role that can be *present but wrong*, not just present-or-absent. A naive "any HERALD_TOKEN
value means operator" stub would (a) be a trivial bypass and (b) be unable to produce the
"wrong role" scenario at all. The `<role>:<token>` format is a deliberately minimal stub
encoding -- real JWT parsing/signature verification is exactly the kind of "the actual
implementation is Epic 9's scope" the story's own AC draws a line around, but the stub still had
to be non-trivially bypassable to make the middleware review-worthy at all.

**Judgment call: `~/.herald/config` is JSON, not another `.env`-style format.** No existing
convention in this package's own `~/.claude/.credentials.json` handling (`mcp_transport.py`'s
`resolve_design_credential`) dictated a shape; JSON with a `role` field is the smallest schema
that satisfies the AC's two config-file scenarios (operator vs. a different role) without
inventing anything speculative (no token rotation, no expiry -- unlike the Design credential,
this stub role file has no lifecycle to model yet).

**Follow-up review recommended: true.** This is the one Epic 6 module whose review-worthiness
depends on a real second reviewer independently trying to poke a hole in the gate (bypass paths,
env-var precedence surprises, the config-file JSON parsing edge cases) -- the same caveat Story
1.3/1.6's own specs recorded for comparably security-adjacent surfaces, and for the same reason:
a same-agent self-review is structurally the weakest check on "is this genuinely hard to bypass."

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 424 passed, 2 skipped
  (whole-package total after all five Epic 6 stories).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `HERALD_TOKEN=operator:x herald success publish claim-1 <<< y` -- exit 0, "authorized" printed.
- `herald success publish claim-1 <<< y` (no env var) -- exit 1, "auth context missing".

## Spec Change Log

## Review Triage Log

### 2026-08-07 -- Self-review pass (single agent, no independent second reviewer)

Adversarial re-read specifically targeting: is the gate a genuine check or an easy-to-bypass one;
does every write path go through it; does the confirmation prompt ever block a test.

- No patch-worthy findings. The gate was checked against three concrete bypass attempts during
  this pass, all of which correctly failed: (1) setting `HERALD_TOKEN` to an arbitrary non-empty,
  non-colon-delimited string -- resolves to no auth context, not operator (see the "malformed"
  row in the I/O matrix); (2) calling `_run_success_publish`/`_run_notice_author` with the auth
  check somehow skipped is not reachable from the CLI at all -- `require_operator_role` is
  unconditionally the first statement in each `operation` closure, with no branch that runs
  before it; (3) a `viewer`-role context is distinguishable from "missing" (different message,
  same exit code) -- proven by dedicated tests for both.
- `addressed_findings`: 0. No `intent_gap`, no `bad_spec`, no `defer`, no `reject`. This entry
  exists to record that the adversarial pass ran and found nothing to patch, per this repo's own
  "genuine adversarial self-review pass on your own diff" instruction -- not merely a formality.

**Follow-up review recommendation stands (see Design Notes above) despite zero findings here:** a
same-agent pass finding nothing is weaker evidence than an independent second pass finding
nothing, precisely because the reviewer already knows how the gate is supposed to work and is
less likely to think adversarially about ways around it that were never considered during
implementation.
