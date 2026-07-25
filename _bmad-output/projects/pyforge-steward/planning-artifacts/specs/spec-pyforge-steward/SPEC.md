---
surface:
  - src/shared/packages/pyforge-steward/**  # the CLI this Spec builds (not yet created)
id: SPEC-steward
companions:
  - ../../architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-steward.md
  - ../../briefs/brief-pyforge-steward-2026-07-25/brief.md
  - ../../prds/prd-pyforge-steward-2026-07-25/prd.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Steward (pyforge-steward) — the estate the factory stands on

## Why

A mandate this repo has already paid for meeting late, twice: `_http.py` attached the `JFROG_API_KEY` auth header to every outbound request regardless of destination host until a human caught it, and on 2026-07-24 a committed `sk-ant` key needed git history rewritten and the key rotated. Both are the same underlying gap — privilege that outlived its intended scope, caught after the fact rather than prevented — and nothing in the pyforge Guild owned "no privilege outlives its deployment" as a first-class responsibility until the 2026-07-23 ownership audit found Deployment & Operations orphaned. Steward (module `pyforge.steward`, CLI `steward`) is that station: it provisions the engines the factory runs on, deploys the services it ships, holds the keys that guard it, and enforces the budget ceilings that bound it. It is not a new platform — domain and technical research both converge on the same verdict: a thin CLI formalizing what this repo's maintainer already does by hand, cloning the already-shipped `pyforge-warden` packaging pattern rather than reimplementing Vault, Backstage, ArgoCD, or Kubecost at a scale this one-person factory doesn't have.

## Capabilities

- **CAP-1**
  - **intent:** An operator can issue, scope, rotate, audit, inventory, and record revocation of credentials through one CLI (`steward keys`), with the historical `JFROG_API_KEY` cross-host leak pattern closed as a named automated regression test.
  - **success:** A credential declared with an explicit host allowlist is never attached to a request outside it; `encrypt`/`decrypt` round-trips a fixture exactly via `age`; `rotate` re-encrypts every secret under a newly generated identity and the old identity fails to decrypt afterward, with no calendar/cron auto-rotation path; `audit --drift` reports the historical unconditional-injection pattern against a fixture and reports clean against today's fixed `_http.py`; `list` enumerates identities with scope/last-rotated metadata and never prints a raw secret value under any flag; `revoke` marks an identity retired and prints manual remediation guidance with zero third-party API calls; a dedicated conformance test fails loudly if the host-gating logic is ever removed or bypassed.
- **CAP-2**
  - **intent:** An operator can build and publish the Pages dashboard through one reconciled command (`steward deploy dashboard`) instead of hand-running `dashboard-gen` + `git push`.
  - **success:** Running twice with no source change between runs results in zero commits on the second run; a real change to the generated output results in exactly one new commit containing exactly the changed files, pushed to the existing Pages-serving branch; `--dry-run` performs the build+diff and prints it without committing or pushing; `status` reports the last successful deploy's commit SHA and timestamp read from Git history alone, with no separate state store.
- **CAP-3**
  - **intent:** An operator or an unattended bmad-loop session can materialize any named pixi environment or a bmad-loop runner+environment together, list what exists, and verify the `environment.yaml` sync gate, without recalling raw pixi/`bmad-loop-worktree` syntax.
  - **success:** A valid environment name materializes via `pixi install -e`; an invalid name reports a clear error listing valid names rather than surfacing pixi's raw error; `--runner bmad-loop --env <name>` wraps `scripts/bmad-loop-worktree` to materialize a worktree plus its named environment in one call, surfacing underlying failures clearly rather than leaving orphaned state unreported; `--list` enumerates every `pixi.toml` `[environments]` entry with its composing features (plus `--json`); `--verify` wraps the existing sync-gate check and reports drift with a non-zero exit when out of sync.
- **CAP-4**
  - **intent:** An operator can declare and query a machine-readable resource ceiling and get an honest signal about spend rather than a fabricated number.
  - **success:** `budget set --cap <amount><currency>/<period>` records a stable, documented schema and rejects a malformed cap value without writing a corrupt entry; `budget show` prints the declared ceiling(s) in human and `--json` form, and reports clearly (not a crash or misleading zero) when none is declared; `budget check` returns one of three distinct exit codes — not-configured / under-budget / over-budget — never collapsing "no data" into a pass, with no cloud-cost-SDK or Kubecost/OpenCost/Infracost client import anywhere in the codebase.

## Constraints

- **AD-1 (wrap, never reimplement):** every duty adapter's implementation is a subprocess call or a thin import into an existing tool (`_http.py`, `age`, `pixi`, `git`, `gh`, `scripts/bmad-loop-worktree`). A duty module containing its own copy of logic that already exists elsewhere in this repo is a review-blocking finding.
- **AD-2 (keys' single chokepoint):** `steward.keys`'s host-scoping resolver delegates to `_http.py`'s existing `auth_headers_for(url, skip_auth=...)` pattern for anything HTTP-shaped; no duty module constructs its own request carrying ambient auth headers. Host-allowlist configuration reads `_http.py`'s existing `resolve_*_urls`/`*_BASE_URL` table directly — no duplicate Steward-owned URL config.
- **AD-3 (age-encrypted at rest, no standing service):** `age`/`age-keygen` are required external pixi run-dependencies, never vendored or reimplemented; `steward keys encrypt/decrypt/rotate` shell out to the `age` CLI. No Vault/Infisical-class secrets-manager server enters the dependency graph.
- **AD-4 (deploy is CLI-invoked reconciliation only):** `steward deploy dashboard` computes a diff (freshly-built output vs. the committed tree) before any git mutation; a no-diff run performs zero commits. No daemon, scheduler, or new GitHub Actions workflow ships in v1 — the operator or an existing workflow invokes the CLI directly against the existing Pages-serving branch.
- **AD-5 (provision wraps, never forks, Marshal-owned machinery):** `steward provision` subcommands shell out to `pixi install -e <name>` and `scripts/bmad-loop-worktree` verbatim; Steward's own code reads `pixi.toml`'s `[environments]` table for inventory but never writes to it and never re-implements pixi's resolution logic.
- **AD-6 (budget v1 is declared-not-enforced):** `steward budget check` returns one of three distinct exit codes — not-configured, under-budget, over-budget — never collapsing "no data" into a pass. No cost-integration import exists in the codebase until a future story adds a real metered spend source.
- **AD-7 (one shared Duty protocol; missing duty degrades, never crashes):** every duty module exposes a `Duty`-protocol-conforming object; `cli.py` dispatches through the protocol only. A duty not yet implemented for a given subcommand returns a result carrying an explicit "not implemented" status rather than raising.
- **AD-8 (exit-code sole ownership):** `main()` is the only place that returns a process exit code — it catches `KeyboardInterrupt`, `SystemExit` raised inside a duty, and any other `Exception` with fixed, documented codes, never the bare interpreter default `1`. A duty module never calls `sys.exit` directly.
- **AD-9 (enterprise routing inherited, never duplicated):** any new outbound HTTP endpoint Steward introduces is added as one new row to `_http.py`'s existing `resolve_*_urls` convention — never a parallel Steward-specific config mechanism.
- **Credential provenance convention:** `steward keys list` entries carry a `provenance` field, `issued` (an `age` identity Steward itself minted) or `observed` (a pre-existing repo credential Steward's audit discovered but did not create). Both are listed for drift-audit visibility; only `issued` entries are rotatable via `steward keys rotate` in v1.
- **Credential values are never printed:** `steward keys list`/`audit` output never contains a raw secret value under any flag combination — enforced by a dedicated invariant test.
- **Provision's pixi invocations are explicit, user-triggered CLI actions only** — never an import-time or build-time side effect.
- **Config file location:** repo-root `.steward/` dotdir, tracked (not gitignored, not under `_bmad-output/`) — `budget.yaml`, `keys-inventory.yaml`, and `*.age` payloads all live here, surviving a `bmad-switch` to a different active BMAD project, since a durable operational fact does not belong under a per-project planning-artifacts tree.

## Non-goals

- No standing secrets-manager service (Vault/Infisical/OpenBao-class server) — `keys` is a CLI + encrypted files only.
- No Backstage-class software catalog or scaffolder platform — `provision` is a CLI face over pixi, not a new IDP.
- No ArgoCD/Flux-class GitOps control plane — `deploy`'s reconciliation is CLI-invoked, not a standing controller.
- No Kubecost/OpenCost/Infracost-class cost-allocation integration in v1 — no live cloud spend exists to allocate against yet.
- No third-party credential-revocation API integration (JFrog, GitHub, Anthropic) — `keys revoke` records intent and guides manual remediation, it does not call provider APIs.
- No `presenton-pixi-image` on OpenShift or air-gap bundle install support in v1 — `deploy`'s v1 scope is the Pages dashboard only.
- No multi-operator / team features — single-operator dogfooded tooling.
- No calendar-based automatic key rotation scheduler — rotation in v1 is on-demand/risk-triggered.

## Success signal

The `JFROG_API_KEY` cross-host leak pattern has a passing, named regression test in Steward's conformance suite, and `steward deploy dashboard` replaces 100% of manual `dashboard-gen` + push invocations going forward. Supporting: `steward provision --env <name>` succeeds for every entry in the pixi estate without the operator consulting raw pixi syntax; `steward budget show` is queried at least once after any Dream/spec update touching the ceiling doctrine. Counter-signals that must NOT be optimized away: the number of duties/features shipped (a `budget` duty growing Kubecost-scale before real spend exists is over-building), and key-rotation frequency as a vanity metric (more rotations is not better).

## Assumptions

- Steward has exactly one user (this repo's maintainer, acting through every other pyforge persona and every bmad-loop session); no team/multi-tenant surface — not independently re-validated with the user this session.
- Third-party credential-revocation API integration is out of scope for v1 because Steward has no existing credential to call such APIs with today — inferred, not user-confirmed.
- The `1500usd/month` figure in the ceiling-declaration example is illustrative, carried from the Dream's own CLI cadence example — the actual ceiling value is a config input, not a Spec claim about real spend.
- `age`-based at-rest encryption (constraint AD-3) is the PRD's own lowest-confidence decision (flagged for architecture confirmation) — assumed durable only while Steward's secret inventory stays a handful of API keys; revisit if it grows materially.
- Direct-push deploy with no new GitHub Actions workflow (constraint AD-4) is a medium-confidence decision — assumed sufficient until scheduled/push-button deploy automation becomes a real want, at which point it should be revisited, not silently reversed.
