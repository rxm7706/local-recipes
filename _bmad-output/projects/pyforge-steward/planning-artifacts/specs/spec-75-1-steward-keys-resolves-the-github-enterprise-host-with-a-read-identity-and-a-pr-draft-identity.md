---
title: "75.1: `steward keys` resolves the GitHub Enterprise host with a read identity and a PR-draft identity"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '8ee966160da0ad699795a1381cd3c66bbf9f6ed4'
warnings: [oversized]
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.steward.ghe_fleet_credentials
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need Guild CAP-5 (steward Epic 76); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: keys exec is listed as disabled and exits 2; the resolver resolves no enterprise host (github.com only, as today)
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - .steward/keys-inventory.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Warden's fleet scan must reach the enterprise fleet on GitHub Enterprise (operator ruling 2026-09-28), and a
fix PR on a fleet repo opens only after the operator approves that proposal. `keys.py`'s `HostScopedCredential` /
`resolve_headers` (FR-7, Story 1.2) decides only host membership and delegates every header to `_http.auth_headers_for`,
which attaches `GITHUB_TOKEN` / `GH_TOKEN` only when the host contains `github.com`; a GHES host named by
`GITHUB_API_BASE_URL` (`resolve_github_api_urls`, the existing row) falls to the JFrog branch or netrc, so no GitHub token
reaches it. `.steward/keys-inventory.yaml` (FR-5) holds three `observed` rows and no issued GitHub identity, and no
`steward keys` verb hands a secret to another process. Warden's Story 16.1 is minted `blocked` on this story in warden's
ledger.

**Approach:**

- **The host.** `keys.py` reads the enterprise host as the hostname of `_http.resolve_github_api_urls()[0]` when
  `GITHUB_API_BASE_URL` is set and that host is not `github.com` / `api.github.com` (AD-9: no Steward-owned URL config).
  Unset, no enterprise host exists and nothing resolves for one.
- **The attachment (AD-2, amended 2026-09-28).** An issued enterprise identity is a `HostScopedCredential` whose hosts are
  that one host; `resolve_headers` returns `{"Authorization": "Bearer <token>"}` only when the URL's canonical host equals
  it, and `{}` otherwise — exact match, as `_canonical_host` already does, so a suffix or prefix look-alike gets nothing.
  Every other credential path still delegates to `auth_headers_for`; `.claude/skills/conda-forge-expert/scripts/_http.py`
  does not change, so no CFE retro is owed.
- **The two scopes.** `ghe-fleet-read` (clone and contents read, for the scan) and `ghe-fleet-pr-draft` (pull-request
  drafts, only for an approved proposal) are `issued` inventory rows, each with its own age payload under `.steward/`,
  rotated by the existing `steward keys rotate --scope`. The token's permissions are set when the operator issues it in
  GitHub Enterprise; the how-to names them. `keys audit` gains a finding when one payload serves both scopes.
- **The only delivery path.** `steward keys exec --scope <scope> [--approval <ref>] -- <argv>` decrypts the scope's payload
  with the operator's age identity, builds the child's environment from the parent's minus `GITHUB_TOKEN`, `GH_TOKEN`,
  `GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN`, adds `GH_HOST` (the enterprise host) and `GH_ENTERPRISE_TOKEN` (the
  token), and runs the child through `pyforge.core.process`; its exit code is returned through `main()` (AD-8). The token
  never appears on argv, stdout, stderr or in a log. `--scope ghe-fleet-pr-draft` refuses with exit 2 unless `--approval`
  names a non-empty reference, and then appends one line — UTC time, scope, approval reference, the child's `argv[0]`,
  never the token — to `.steward/keys-exec.log` (gitignored by `*.log`). `--scope ghe-fleet-read` never yields the draft
  payload.
- **The flag.** `pyforge.steward.ghe_fleet_credentials` enters `src/platform/config/flags.json` with variants `on` / `off`
  and `defaultVariant: off`. OFF: `keys exec` stays in `--help`, marked disabled, and exits 2 (steward's usage code) with
  a flag-off message; the resolver resolves no enterprise host.
- **The fleet-wide CLI flag contract** (coordinator ruling 2026-09-28: this story is the home of
  `pyforge.core.flags.read_boolean`). No station CLI can read a boolean flag today — `pyforge.core` holds only the
  `cutover_root` string reader, and `django_pyforge.flags` is reachable only inside the host. This story adds
  `src/shared/packages/pyforge-core/src/pyforge/core/flags.py` in `pyforge.core.cutover_root`'s shape (Story 44.12's
  precedent: a steward-authored CLI reader in `pyforge-core`, co-governed by `spec-pyforge-core`). **Every other station's
  flagged CLI story reuses these names and never re-implements them**, so the shape below is a fleet contract; after this
  story lands it changes only additively:
  - **Signature:** `read_boolean(key: str, default: bool = False, *, flags_path: Path | str | None = None) -> bool`.
  - **Tree resolution:** exactly `pyforge.core.cutover_root.resolve_flags_path` — reused, not copied: the explicit
    `flags_path`, else `PYFORGE_FLAGS_PATH`, else the nearest `src/platform/config/flags.json` walking up from the working
    directory.
  - **OFF and absent semantics:** `state: DISABLED` reads False whatever else is set (the kill switch wins). A present key
    reads its `defaultVariant`'s value when that value is a bool. A missing tree, an unreadable tree, a missing key or a
    non-bool value reads `default`, with one named WARN on stderr naming the key and the reason. A new capability passes
    `default=False`, so it never reads ON by accident; only a retrofit kill switch (`spec-feature-flag-governance` CAP-7)
    may pass `default=True`.
  - **The Q3 helpers:**
    - `FlagOff(Exception)` carries the key and the message `flag <key> is off`.
    - `require(key, default=False, *, flags_path=None) -> None` raises `FlagOff` when `read_boolean` is False.
    - `disabled_help(help_text, key, default=False, *, flags_path=None) -> str` returns the help text with
      ` [disabled: flag <key> is off]` appended when the flag is off, and the text unchanged when it is on, so the verb
      stays listed in `--help`.
    - The helpers never choose an exit code. Each station's `main()` catches `FlagOff` and returns its own usage code: 2
      for steward, which `main()` already owns under AD-8. No station's frozen exit-code domain changes.
  - **Later changes keep the contract:** Story 76.1 makes `read_boolean` read the per-environment rendered tree, and
    Story 76.3 routes its evaluation through OpenFeature. Neither changes the signature, the resolution order or the
    OFF/absent semantics.
  - **Dispatch this story first,** before any other station's flagged CLI story. It is ready now (Deps none).
  - This story adds no OpenFeature dependency.
- **The record.** A how-to section (beside `docs/how-to/ocp-cluster-bringup.md` § 5's recording procedure) says how the
  operator issues the two tokens, encrypts each with `steward keys encrypt`, and records the two rows. The real rows land
  when the operator issues the tokens; the tests use fixture inventories.
- Nothing inbound: no webhook route, no listener. Deployed pods carry secret references only (canopy:AD-19); the chart
  wiring belongs to the story that deploys the fleet scan.

Ledger key: `75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-164 (FR-37; extends FR-5, FR-7); AD-2 (amended 2026-09-28), AD-3 (age), AD-8 (exit codes),
  AD-9 (the host from `_http.py`'s existing row); canopy:AD-19.
- `spec-feature-flag-governance` CAP-1 (the flag block), Q3 (a flag-off verb stays listed and exits with the usage code,
  the helpers' contract); CAP-5, whose Stories 76.1 and 76.3 extend the reader this story adds without changing its shape;
  CAP-7 (a retrofit kill switch may pass `default=True`); the Guild constraint that station code reads flags only through
  `pyforge.core` or `django_pyforge.flags`.
- Coordinator ruling 2026-09-28: steward 75.1 is the home of `pyforge.core.flags.read_boolean`; its shape is the
  fleet-wide contract other stations' flagged CLI stories reuse, and it dispatches first.
- Kinship: warden Story 16.1 (warden's chain, `blocked` on this story); `docs/dreams/work-passports-dated-extracts.md` (no
  PAT that opens their org or writes ours on their behalf).

## Acceptance Criteria

- Given `GITHUB_API_BASE_URL=https://ghe.example.test/api` and an issued `ghe-fleet-read` credential When `resolve_headers` runs Then `https://ghe.example.test/api/v3/repos/o/r` gets a Bearer header, and `https://api.github.com/…`, `https://other.test/…`, `https://evil-ghe.example.test/…` and `https://ghe.example.test.evil.test/…` get `{}`
- Given `GITHUB_API_BASE_URL` unset When `resolve_headers` runs for any non-github host Then no enterprise identity resolves
- Given `steward keys exec --scope ghe-fleet-read -- <probe>` with a planted token and ambient `GITHUB_TOKEN` / `GH_TOKEN` set When it runs Then the probe's environment holds `GH_HOST` and `GH_ENTERPRISE_TOKEN` equal to the read token and none of the four ambient variables from the parent, and the token appears in no argv, no stdout or stderr of the parent, and no journal line
- Given `steward keys exec --scope ghe-fleet-pr-draft -- <probe>` without `--approval` When it runs Then it exits 2 and the probe never starts
- Given the same with `--approval PROP-7` When it runs Then the probe gets the draft token and `.steward/keys-exec.log` gains one line naming `PROP-7`, the scope and the probe's `argv[0]`, and not the token
- Given `steward keys exec --scope ghe-fleet-read` When the child's environment is read Then it never holds the draft token
- Given an inventory whose two scopes point at one payload When `steward keys audit` runs Then it reports that finding and exits 1
- Given `steward keys list` and `steward keys audit` When they run over the two rows Then neither prints a secret value, and `steward keys rotate --scope` re-encrypts each row's payload
- Given two flagd trees, the flag on and off When `keys exec` and `resolve_headers` run Then OFF exits 2 with a flag-off message, `--help` lists `exec` as disabled, and no enterprise host resolves; ON behaves as above
- Given a tree with a boolean key `on`, the same key `off`, the key `state: DISABLED` with an `on` default, a missing key, a string-valued key, a malformed tree and no tree at all When `pyforge.core.flags.read_boolean` reads each with `default=False` Then it returns True, False, False, and False with one named WARN for each of the last four; with `default=True` the last four read True (with the WARN) and `state: DISABLED` still reads False
- Given `flags_path` unset When `read_boolean` resolves the tree Then it calls `pyforge.core.cutover_root.resolve_flags_path` (explicit path, `PYFORGE_FLAGS_PATH`, then the walk-up), and a test pins that no second resolver exists in `pyforge.core`
- Given the key off When `require` runs Then it raises `FlagOff` naming the key; and `disabled_help("run a child", key)` returns the text with ` [disabled: flag <key> is off]`; on, `require` returns and `disabled_help` returns the text unchanged
- Given `FlagOff` raised inside a steward duty When `main()` handles it Then steward exits 2 with the flag-off message on stderr, and `pyforge.core.flags` itself defines no exit code
- Given the change When `test_keys_host_scoping.py`'s `JFROG_API_KEY` regression and `pixi run --frozen -e pyforge-steward pyforge-steward-test` run Then both pass

## Boundaries & Constraints

**Always:**
- Keep host membership in `keys.py`; read the host from `_http.py`'s existing `GITHUB_API_BASE_URL` row.
- Deliver a token only through a child's environment; scrub the four ambient GitHub token variables first.
- Update the duty and verb counts in `tests/unit/test_cli.py` (and `test_restore_duty.py` if it counts verbs) when `exec`
  joins `keys`.
- Reconcile every Spec `spec-surface-check` names (`spec-pyforge-steward`; `spec-pyforge-core` co-governs every station's
  `src/`), then stamp each scoped with `--spec`.
- Keep `pyforge.core.flags` stdlib-only and importable by every station, with a module docstring stating that it is the
  fleet-wide CLI flag contract. The signature, the resolution order, the OFF/absent semantics and the Q3 helpers change
  only additively from here.

**Never:**
- Do not give `pyforge.core.flags` an exit code, a second tree resolver, an environment-variable provider or any
  station-specific logic.
- Do not edit `.claude/skills/conda-forge-expert/scripts/_http.py` or any CFE surface.
- Do not accept a secret through a CLI flag, print one, or write one to a log or journal.
- Do not add a webhook, a listener, a scheduler or a GitHub API call (no provider API integration, no calendar rotation).
- Do not commit a real token or a real enterprise hostname; tests use fixtures.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`; do not flip warden's `blocked` row.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| enterprise URL | host equals the GHE host | Bearer header | — |
| github.com | `api.github.com` | `{}` from this credential | ambient path unchanged |
| look-alike | suffix or prefix of the host | `{}` | — |
| no base URL | `GITHUB_API_BASE_URL` unset | nothing resolves for an enterprise host | — |
| read exec | `--scope ghe-fleet-read` | child env: `GH_HOST`, read token; ambient tokens gone | child's exit code returned |
| draft exec, no approval | `--scope ghe-fleet-pr-draft` | child never starts | exit 2 |
| draft exec, approved | `--approval PROP-7` | child runs; journal line without the token | — |
| shared payload | both scopes, one `.age` file | audit finding | exit 1 |
| flag OFF | any `exec` | listed as disabled | exit 2, flag-off message |
| reader cannot read | no tree, unreadable tree, no key, non-bool value | reads `default` (False for this flag), so OFF | named WARN on stderr, exit 2 |
| kill switch | `state: DISABLED` | OFF, whatever `default` says | exit 2 |
| no age identity | decrypt fails | child never starts | named error, exit 1 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- `HostScopedCredential` (l.109; frozen, `hosts` only), `_canonical_host` (l.179), `resolve_headers` (l.207; today delegates every header to `auth_headers_for`), `load_inventory`/`_locked_inventory`/`rotate_identity` (l.608-847; the age-payload + identity-row shape to reuse), `decrypt_file` (l.433), `_run_audit` (l.999), `_KEYS_VERBS` + `KeysDuty.run` (l.996, 1048). Import-time `_http` bridge (l.100-104) supplies `resolve_github_api_urls`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- `_add_keys_subparsers` (l.281; verb metavar l.286), `main()` (l.1398; the only exit-code owner; `DutyResult.details["exit_code"]` override l.1417; `EXIT_USAGE = 2` l.21). `budget.py` l.300 is the precedent for a duty importing an `EXIT_*` from `.cli` inside the function.
- `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py` -- `resolve_flags_path` (the one tree resolver), `ENV_FLAGS_PATH`, `LOCAL_DEV_RELATIVE`; the shape `flags.py` follows. Read-only here.
- `src/shared/packages/pyforge-core/src/pyforge/core/process.py` -- `PosixProcess.run` inherits `os.environ` and has no `env=`; `ProcessPort` Protocol is shared with fakes in other stations, so only the concrete class gains an optional `env`.
- `.claude/skills/conda-forge-expert/scripts/_http.py` -- `resolve_github_api_urls` (l.964, `[0]` is `GITHUB_API_BASE_URL` when set), `auth_headers_for` (l.417). Read-only; no CFE retro owed.
- `src/platform/config/flags.json` -- the one flagd tree (`{"flags": {key: {state, variants, defaultVariant}}}`); shape pinned by `src/platform/tests/test_openfeature_file_flags.py::_flagd_tree`.
- `.steward/keys-inventory.yaml` -- three `observed` rows; unchanged (real rows land when the operator issues the tokens). `.gitignore` l.375 `*.log` already ignores `.steward/keys-exec.log`.
- `docs/how-to/ocp-cluster-bringup.md` -- § 5 *Keys discipline* is the recording procedure the new § 5.1 sits beside.
- `src/shared/packages/pyforge-steward/tests/unit/test_keys_rotate.py` -- fixture style (real `age`/`age-keygen`, `generate_identity`, `save_inventory`); `test_keys_host_scoping.py` holds the `JFROG_API_KEY` regression that must stay green.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-core/src/pyforge/core/flags.py` -- add `read_boolean`, `FlagOff`, `require`, `disabled_help` exactly as the contract states; stdlib-only, resolves the tree through `cutover_root.resolve_flags_path`, one stderr WARN per absent/unreadable/malformed/non-bool read, no exit code; module docstring names it the fleet-wide CLI flag contract -- Story 44.12 precedent, reused by every flagged CLI story.
- `src/shared/packages/pyforge-core/src/pyforge/core/process.py` -- give `PosixProcess.run` an optional keyword-only `env: Mapping[str, str] | None = None` passed to `subprocess.run`; `ProcessPort` and the class docstring updated to say the default still inherits -- lets `keys exec` hand the child a scrubbed environment without touching any other caller.
- `src/platform/config/flags.json` -- add `pyforge.steward.ghe_fleet_credentials` (`on`/`off`, `defaultVariant: off`) -- the flag block in the frontmatter.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- (a) `HostScopedCredential.bearer_token` (`repr=False`, `compare=False`, default `None`) and a `resolve_headers` branch: token set gives `{"Authorization": "Bearer <token>"}` on an exact canonical-host match and `{}` otherwise; token unset delegates unchanged; (b) `enterprise_host()` (hostname of `resolve_github_api_urls()[0]` when `GITHUB_API_BASE_URL` is set, not `github.com`/`api.github.com`, and the flag is on; else `None`) and `enterprise_credential(inventory_path=None, scope="ghe-fleet-read")`; (c) `exec` verb: flag `require`, approval gate, journal line, payload decrypt into a private temp dir, scrubbed child env, `PosixProcess.run(env=...)`, token-redacted relay of the child's streams, exit code through `details["exit_code"]`; (d) `_run_audit` gains the shared-payload finding -- FR-37 delivery path and AD-2 amendment.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- `exec` subparser (`--scope` choices, `--approval`, `--inventory`, remainder argv after `--`), help built with `disabled_help`, metavar and audit `--inventory` added, `main()` catches `FlagOff` and returns `EXIT_USAGE` with the message on stderr -- AD-8 stays the one exit-code owner.
- `docs/how-to/ocp-cluster-bringup.md` -- new § 5.1: issue the two GHE tokens with the permissions each scope needs, `steward keys encrypt` each, record the two `issued` rows, run `keys exec`; no real host or token -- the record.
- `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, `test_process.py` -- `read_boolean`/`FlagOff`/`require`/`disabled_help` cases, the one-resolver pin, and the `env=` pass-through.
- `src/shared/packages/pyforge-steward/tests/unit/test_keys_ghe_credentials.py`, `tests/unit/test_cli.py` -- resolver matrix, exec matrix (probe child writes its env to a file), audit finding, ON/OFF trees, `FlagOff` in `main()`, `exec --help` (verb and count assertions updated).
- Owning Spec memlogs -- one `Surface reconcile 2026-09-29` entry per governed path on `spec-pyforge-steward` and `spec-pyforge-core` (and any co-governor `spec-surface-check` names); then a scoped stamp for each.

**Acceptance Criteria:**
- Given the intent contract's fourteen Given/When/Then criteria above, when `pixi run --frozen -e pyforge-steward pyforge-steward-test` and the `pyforge-core` unit suite run, then every one passes and `test_keys_host_scoping.py`'s `JFROG_API_KEY` regression stays green.
- Given the diff, when `python scripts/spec_surface_reconcile.py` runs, then it exits 0 with every changed governed path named on its Spec's `.memlog.md`.

## Spec Change Log

## Design Notes

- The token rides on the credential object (`bearer_token`, `repr=False`) rather than being looked up inside `resolve_headers`, so the function stays a pure host gate; `enterprise_credential` is the only place that decrypts.
- `keys exec` is the single reader of a payload for a child; `enterprise_credential` decrypts the read scope for in-process HTTP callers, never the draft scope.
- The audit's shared-payload finding compares resolved paths of the two scopes' active `issued` payloads; it runs on every `keys audit`, and prints a `[inventory] clean` line only when `--inventory` is given, so the existing flag-less and `--drift`/`--secrets` output is unchanged.
- A child killed by signal `-N` exits `128 + N`, so `main()` never returns a negative code.

## Source

Contract authored from `docs/dreams/pyforge-steward.md`'s 2026-09-28 (night) Realization-log entry *Proposed: Warden's
fleet scan reaches GitHub Enterprise with host-scoped credentials the key inventory holds*, the Warden Dream's entry of the
same night, and `spec-pyforge-steward` CAP-164 with its direction and route-decision entries in the Spec's `.memlog.md`.

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-164 (FR-37).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 (night) — Proposed: Warden's fleet scan reaches GitHub Enterprise with host-scoped credentials the key inventory holds*.
Ledger key: `75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`.
Ledger status at mint: `backlog`.
Deps: —. Dispatch first: this story is the home of `pyforge.core.flags.read_boolean` and its Q3 helpers, the fleet-wide
contract every station's flagged CLI story reuses (coordinator ruling 2026-09-28). Warden Story 16.1 waits on this story
as a `blocked` row in warden's ledger; steward Story 76.1 extends the reader (`Deps: S-75.1` there).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- ON/OFF: the `keys exec` tests write two flagd trees (flag on, flag off), the way
  `src/platform/tests/test_openfeature_file_flags.py` does, and assert the OFF verb is listed as disabled and exits 2
  (until the testing-kit fixture of `spec-feature-flag-governance` CAP-4 lands).
- `pixi run --frozen -e pyforge-guild steward keys exec --help` — expected: `--scope`, `--approval`, and no flag that takes a secret.
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q` — expected: pass
  (`read_boolean`'s cases); `pyforge-core`'s own coverage floor holds for the new module.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
