---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
mode: headless-express
updated: '2026-08-15'
currency_review: "Reviewed 2026-08-15 (fleet-wide decomposition audit) — Story 8.7 added (FR-140, spec-jira-github-projects-sync's CAP-1 residual, previously undecomposed per Story 8.1's own AF-5 audit note); spec-pyforge-steward and spec-bmad-module-provisioning frontmatter status fields corrected (blank/stale-draft -> shipped, both fully decomposed and done). Prior review 2026-08-10 (Phase 1 backlog-truth audit) — 10 false Status lines corrected, Epic-8 audit note + 8.1 delivery note added; see planning-artifacts/implementation-readiness-report-20260810.md. Prior review 2026-08-02."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (AD-72).
epics_role: canonical
---

# pyforge-steward - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for **Steward** (`pyforge-steward`), decomposing the PRD's FR-1..FR-18 (across the four duties: keys, deploy, provision, budget) and the architecture spine's AD-1..AD-9 into implementable stories. Run headless/express per the calling task's directive — elicitation gates in the underlying `bmad-create-epics-and-stories` skill (epic-structure approval, per-story review) were self-confirmed rather than presented interactively; deviations from the two input documents' tentative suggestions are called out explicitly where made.

## Requirements Inventory

### Functional Requirements

FR-1: Host-scoped credential resolution — any Steward-issued or Steward-audited credential attachment is gated by the request's destination host (extends `_http.py`'s `skip_auth` guard).
FR-2: At-rest secret encryption via `age` — `steward keys encrypt`/`decrypt` wrap the `age` CLI so secrets live encrypted in Git, never as committed plaintext.
FR-3: Key rotation — `steward keys rotate --scope <name>` generates a new `age` identity, re-encrypts affected secrets, retires the old identity.
FR-4: Credential audit / drift detection — `steward keys audit --drift` scans tracked scripts/config for HTTP-credential-attachment code paths that are not host-scoped.
FR-5: Credential inventory — `steward keys list` enumerates known credential identities with scope + last-rotated metadata, never printing secret values.
FR-6: Revocation record — `steward keys revoke --scope <name>` marks an identity retired and prints manual remediation guidance (no third-party API calls).
FR-7: Remediation regression test — the `JFROG_API_KEY` cross-host leak pattern is closed as a named, automated regression test.
FR-8: Dashboard build — `steward deploy dashboard --build` runs the existing `dashboard-gen` pixi task.
FR-9: Reconciled push — `steward deploy dashboard` builds, diffs the generated output against the committed tree, and only commits+pushes on a real difference.
FR-10: Dry-run — `steward deploy dashboard --dry-run` performs build+diff and prints the diff without committing/pushing.
FR-11: Deploy status — `steward deploy status` reports the last successful dashboard deploy (commit SHA, timestamp) from Git history.
FR-12: Environment materialization — `steward provision --env <name>` resolves `<name>` against pixi.toml's `[environments]` table and runs `pixi install -e <name>`.
FR-13: Runner provisioning — `steward provision --runner bmad-loop --env <name>` wraps `scripts/bmad-loop-worktree` to materialize a worktree + its named env together.
FR-14: Environment inventory — `steward provision --list` enumerates every environment in pixi.toml's `[environments]` table with its composing features.
FR-15: Sync-gate check — `steward provision --verify` wraps the existing `environment.yaml` ↔ `pixi.toml` sync-gate check and reports drift.
FR-16: Ceiling declaration — `steward budget set --cap <amount><currency>/<period>` records a machine-readable ceiling to a tracked config file.
FR-17: Ceiling display — `steward budget show` prints the current declared ceiling(s) in human and `--json` form.
FR-18: Manual check (honest stub) — `steward budget check` reports "no metered spend source configured" via a distinct exit code rather than fabricating a number.

### NonFunctional Requirements

NFR-1: No standing secrets-manager service — `keys` operates entirely as a CLI + encrypted files in Git (no Vault/Infisical/OpenBao-class server).
NFR-2: No standing GitOps control plane — `deploy`'s reconciliation is a CLI-invoked step, never a continuously-running controller.
NFR-3: `provision` never invokes pixi at import/build time — pixi invocations are explicit, user-triggered CLI actions only, matching `pyforge-warden`'s "pixi is a build/dev-env floor, never a runtime dependency" precedent.
NFR-4: Lean dependency posture — Steward's own `pyproject.toml` dependency set stays targeted (matches `pyforge-warden`'s lean, pure-stdlib-fallback discipline); external tools (`age`, `pixi`, `gh`, `git`) are wrapped, never reimplemented (AD-1).
NFR-5: `argparse`-based CLI with sole-owned exit codes — one dispatcher (`cli.py`) owns every process exit code; no duty module calls `sys.exit` directly (AD-8).
NFR-6: Enterprise/air-gap routing is inherited unchanged from `docs/reference/enterprise-deployment.md` — any new outbound endpoint adds one row to the existing `*_BASE_URL` override table, never a parallel config mechanism (AD-9).
NFR-7: Credential values are never printed — `steward keys list`/`audit` output never contains a raw secret value under any flag combination, enforced by a dedicated `tests/meta/` invariant test.

### Additional Requirements (from Architecture)

- **Starter/scaffold** (Structural Seed): `src/shared/packages/pyforge-steward/` as a pixi build workspace member mirroring `pyforge-warden` — `hatchling` build backend, `pixi-build-python` conda-package wrapper, `[project.scripts] steward = "pyforge.steward.cli:main"`, dedicated `[feature.pyforge-steward]` repo-root pixi block + lean `no-default-feature = true` environment. **This lands in Epic 1 Story 1.1** (the PRD's tentative standalone "Epic E — Packaging & Test Scaffold" is deliberately folded in here rather than kept as its own epic — see Epic Design Note below).
- **Shared `Duty` protocol + exit-code sole ownership** (AD-7, AD-8): `interfaces.py` (`Duty` Protocol + `DutyResult`) and `cli.py`'s exit-code-owning dispatcher are established once, in Epic 1 Story 1.1, and reused unchanged by Epics 2-4.
- **Config file locations** (Consistency Conventions): repo-root `.steward/` dotdir, tracked, independent of the active BMAD project — `budget.yaml`, `keys-inventory.yaml`, `*.age` payloads.
- **Test-tier layout**: `tests/unit/`, `tests/conformance/` (FR-level behavioral contracts, incl. the FR-7 regression test), `tests/meta/` (invariants, e.g. NFR-7) — mirrors `pyforge-warden`'s tree, established in Story 1.1 and populated per-story thereafter.
- **Dogfooding**: `scripts/dogfood_scan.py`-analogue — Steward auditing this repo's own credential surface / provisioning its own dev environment (surfaces in Epic 1 Story 1.6 and Epic 3 Story 3.1's acceptance criteria).

### UX Design Requirements

Not applicable — Steward is a CLI-only tool for a single operator (PRD §2.2); no UX design contract exists or is warranted for v1.

### FR Coverage Map

FR-1: Epic 1 (Keys) - Story 1.2 - host-scoped credential resolver extending `_http.py`
FR-2: Epic 1 (Keys) - Story 1.3 - `age`-based at-rest encryption
FR-3: Epic 1 (Keys) - Story 1.4 - key rotation
FR-4: Epic 1 (Keys) - Story 1.6 - credential audit / drift detection
FR-5: Epic 1 (Keys) - Story 1.5 - credential inventory
FR-6: Epic 1 (Keys) - Story 1.7 - revocation record
FR-7: Epic 1 (Keys) - Story 1.2 - JFROG_API_KEY regression test (carried as an AC of the same story that builds the resolver it regression-tests)
FR-8: Epic 2 (Deploy) - Story 2.1 - dashboard build wrapper
FR-9: Epic 2 (Deploy) - Story 2.2 - reconciled push
FR-10: Epic 2 (Deploy) - Story 2.3 - dry-run
FR-11: Epic 2 (Deploy) - Story 2.4 - deploy status
FR-12: Epic 3 (Provision) - Story 3.1 - environment materialization
FR-13: Epic 3 (Provision) - Story 3.2 - runner provisioning wrapper
FR-14: Epic 3 (Provision) - Story 3.3 - environment inventory
FR-15: Epic 3 (Provision) - Story 3.4 - sync-gate check
FR-16: Epic 4 (Budget) - Story 4.1 - ceiling declaration
FR-17: Epic 4 (Budget) - Story 4.2 - ceiling display
FR-18: Epic 4 (Budget) - Story 4.3 - manual check honest stub

## Epic Design Note (deviation from the PRD's tentative grouping)

The PRD (§11) proposed a tentative "Epic E — Packaging & Test Scaffold" as a possible standalone cross-cutting epic, but flagged the choice explicitly: *"architecture should confirm whether this is its own epic or folded into Epic A's first story."* Per this skill's own epic-design principles (organize by user value, not technical layers — a scaffold-only epic is the textbook "Epic 1: Database Setup — no user value" anti-pattern the skill warns against), the packaging/scaffold work is **folded into Epic 1 (Keys) Story 1.1**, since Keys is both the highest-priority duty (two real, dated incidents) and the first epic built. Epics 2-4 each depend on Epic 1's scaffold existing (the shared `Duty` protocol, the workspace-member packaging, the exit-code-owning dispatcher) — this is a normal, allowed "later epic builds on an earlier epic's output" relationship, not a forward dependency within an epic.

## Epic List

### Epic 1: Keys — Credential Lifecycle
Close the gap this repo has already paid for twice (the `JFROG_API_KEY` cross-host leak, the `sk-ant` key rotation incident): the operator can issue, scope, rotate, audit, inventory, and record revocation of credentials through one CLI, with the historical leak pattern closed as a named regression test. Also establishes the packaging scaffold (workspace member, `Duty` protocol, exit-code-owning dispatcher) every later epic reuses.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7 (+ NFR-1, NFR-4, NFR-5, NFR-6, NFR-7)

### Epic 2: Deploy — Reconciled Dashboard Publishing
The operator can build and publish the Pages dashboard through one reconciled command instead of hand-running `dashboard-gen` + `git push`, with dry-run visibility and a status check — never a wasted commit when nothing changed.
**FRs covered:** FR-8, FR-9, FR-10, FR-11 (+ NFR-2)

### Epic 3: Provision — Environment & Runner Access
The operator (or an unattended bmad-loop session) can materialize any of the pixi estate's environments and bmad-loop runners by name through one CLI, list what's available, and verify the `environment.yaml` sync gate — without recalling raw `pixi install -e` syntax.
**FRs covered:** FR-12, FR-13, FR-14, FR-15 (+ NFR-3)

### Epic 4: Budget — Declared Resource Ceilings
The operator can declare and query a machine-readable resource ceiling, and get an honest signal (never a fabricated number) when asking whether spend is under control — replacing a ceiling doctrine that today lives only in a Dream file's prose.
**FRs covered:** FR-16, FR-17, FR-18

---

## Epic 1: Keys — Credential Lifecycle

Close the `JFROG_API_KEY`/`sk-ant`-class gap and establish Steward's packaging scaffold. Governed by AD-1, AD-2, AD-3, AD-7, AD-8, AD-9.

### Story 1.1: Steward exists as an installable CLI

As the repo maintainer,
I want `pyforge-steward` to install and run as a real package (`steward --version` works) the same way `pyforge-warden` does today,
So that every later duty has a package, a CLI dispatcher, and a shared contract to build against instead of starting from nothing.

**Acceptance Criteria:**

**Given** the repo's pixi workspace
**When** `src/shared/packages/pyforge-steward/` is scaffolded (`pyproject.toml` with `hatchling` backend, `[project.scripts] steward = "pyforge.steward.cli:main"`, `pixi.toml` with `[package.build.backend] name = "pixi-build-python"`) and wired into repo-root `pixi.toml` (`[feature.pyforge-steward.dependencies]` path-dependency into a lean `no-default-feature = true` `pyforge-steward` environment, plus `pyforge-steward-build-conda`/`-build-dist`/`-test`/`-dogfood` tasks mirroring `pyforge-warden`'s task names verbatim)
**Then** `pixi run -e pyforge-steward steward --version` prints a version string and exits 0
**And** `pixi run -e pyforge-steward pyforge-steward-test` runs a passing (if minimal) `pytest` suite under `tests/unit/`, `tests/conformance/`, `tests/meta/`

**Given** `cli.py`'s dispatcher
**When** an `argparse.ArgumentParser` with one subparser per duty (`keys`, `deploy`, `provision`, `budget` — the latter three accepting no verbs yet, since their duty modules land in later epics) is built
**Then** `steward --help` lists all four subcommands
**And** `main()` is the sole owner of the process exit code: it catches `KeyboardInterrupt` (→ a documented SIGINT exit code), `SystemExit` raised inside a duty (→ projected as an internal-error exit, never trusted verbatim), and any other `Exception` (→ a documented internal-error exit, never the bare interpreter default `1`) — per AD-8

**Given** `interfaces.py`
**When** a `Duty` `Protocol` (`name: str`, `run(ns: argparse.Namespace) -> DutyResult`) and a `DutyResult` dataclass are defined
**Then** a minimal `NullDuty`-shaped stub satisfies the protocol and is unit-tested for protocol conformance (mirrors `pyforge-warden`'s `interfaces.py` null-engine precedent) — per AD-7

**And** the repo-root `pixi.toml`'s existing `environment.yaml` sync-gate check still passes after this story's `pixi.toml` edits (CLAUDE.md's ungated CI check)

---

### Story 1.2: Credentials never attach outside their declared host, and the JFrog leak can never recur silently

As the repo maintainer,
I want any credential Steward resolves to be attached only to requests targeting its declared host allowlist, with the historical `JFROG_API_KEY` cross-host leak closed as a named automated test,
So that the exact failure that already happened twice in this repo cannot happen a third time undetected.

**Acceptance Criteria:**

**Given** `steward.keys`'s host-scoped resolver, implemented as a thin wrapper delegating to `_http.py`'s existing `auth_headers_for(url, skip_auth=...)` pattern (per AD-2 — no parallel reimplementation)
**When** a credential is declared with an explicit host allowlist and the resolver is asked for headers against a URL outside that allowlist
**Then** no credential-bearing header is returned
**And** the same resolver asked against a URL inside the allowlist returns the correct credential-bearing header

**Given** a fixture reproducing the historical `_http.py` defect shape (a credential-attachment code path with no host gate, mirroring the pre-fix `JFROG_API_KEY` behavior)
**When** `steward keys audit --drift`-equivalent logic (this story's slice: the underlying detection primitive Story 1.6 later exposes as a full CLI verb) is run against that fixture
**Then** it reports the ungated pattern as a finding
**And** run against the current, already-fixed `_http.py`, it reports clean

**Given** this story's own resolver
**When** `pixi run -e pyforge-steward pyforge-steward-test` runs
**Then** `tests/conformance/` contains a named test asserting the resolver's host-gating behavior fails loudly (test failure) if the gating logic is ever removed or bypassed — this is FR-7's regression test, landing here because it is a direct property of the resolver this story builds, not a separate later concern

---

### Story 1.3: Secrets Steward stores live encrypted in Git, never as plaintext

As the repo maintainer,
I want `steward keys encrypt`/`decrypt` to wrap the `age` CLI,
So that any secret Steward stores can be committed to Git safely, with no standing secrets-manager service to operate.

**Acceptance Criteria:**

**Given** `age`/`age-keygen` declared as external `[feature.pyforge-steward.dependencies]` run-dependencies (never vendored — per AD-3/AD-1)
**When** `steward keys encrypt <file>` is run against a test fixture with a generated `age` identity
**Then** the output file is `age`-encrypted and unreadable without the identity
**And** `steward keys decrypt <file>` with the correct identity reproduces the original bytes exactly (round-trip test)

**Given** a file that plausibly looks like an unencrypted secret (matches a configured "looks like a secret" heuristic)
**When** `steward keys audit` (extending Story 1.2's audit primitive) is run against a directory containing it
**Then** the audit flags it as a plaintext-secret-candidate finding, distinct from the host-gating finding

---

### Story 1.4: Rotating a key never breaks what already trusted it

As the repo maintainer,
I want `steward keys rotate --scope <name>` to generate a new `age` identity, re-encrypt every secret currently encrypted to the old one, and mark the old identity retired,
So that I can respond to a compromise (or just good hygiene) without hand-managing re-encryption myself.

**Acceptance Criteria:**

**Given** one or more secrets encrypted to a named `age` identity (via Story 1.3's `encrypt`)
**When** `steward keys rotate --scope <name>` runs
**Then** every one of those secrets decrypts correctly under the newly generated identity
**And** decrypting any of them under the old identity now fails
**And** the old identity is marked retired in the inventory (Story 1.5's data, updated by this story)

**Given** rotation is invoked with no calendar/cron trigger anywhere in this story's code
**When** the test suite is inspected
**Then** there is no scheduler, cron entry, or time-based auto-rotation path — rotation is on-demand only, per the PRD's risk-triggered-not-calendar-triggered decision (D1... referenced here as the FR-3 rationale)

---

### Story 1.5: The operator can see every credential Steward knows about, never a secret value

As the repo maintainer,
I want `steward keys list` to enumerate known credential identities with scope and last-rotated metadata,
So that I have one place to check what exists instead of grepping env vars and Dream files.

**Acceptance Criteria:**

**Given** `.steward/keys-inventory.yaml` (the tracked, repo-root config location — Consistency Conventions)
**When** `steward keys list` is run after Stories 1.3/1.4 have created/rotated at least one identity
**Then** output includes that identity's name, scope, last-rotated timestamp, and a `provenance` field of `issued` (Steward-minted)
**And** a second entry type, `provenance: observed`, can be manually or auditor-populated (Story 1.6) for pre-existing repo credentials Steward did not create (e.g. a `GITHUB_TOKEN`-class entry) — resolving the PRD's credential-inventory-scope open question

**Given** any flag combination Steward's argparse surface accepts (`--json`, default text, etc.)
**When** `steward keys list` output is inspected
**Then** it never contains a raw secret value — enforced by a dedicated `tests/meta/` test (NFR-7), mirroring `pyforge-warden`'s own invariant-test convention

---

### Story 1.6: The operator can ask "is anything host-unscoped right now?" and get a real answer

As the repo maintainer,
I want `steward keys audit --drift` to scan this repo's tracked scripts/config for HTTP-credential-attachment code paths that are not host-scoped,
So that a future `JFROG_API_KEY`-class defect is caught by a command, not by an incident.

**Acceptance Criteria:**

**Given** Story 1.2's detection primitive and Story 1.5's inventory (observed-entry provenance)
**When** `steward keys audit --drift` is run against this actual repo
**Then** it reports clean against the current, already-fixed `_http.py`
**And** run against a deliberately reintroduced fixture of the historical unconditional-injection pattern, it reports exactly that finding, named clearly enough to locate the offending code path

**Given** this audit is also this duty's dogfooding target (Additional Requirements)
**When** `steward keys audit --drift` is included in the package's own `-dogfood` pixi task (Story 1.1's scaffold)
**Then** the dogfood task exits 0 against the current repo state

---

### Story 1.7: Retiring a credential leaves a record, not a silent gap

As the repo maintainer,
I want `steward keys revoke --scope <name>` to mark an identity retired and print manual remediation guidance,
So that "this credential should no longer be trusted" is recorded even when Steward has no API to revoke it upstream itself.

**Acceptance Criteria:**

**Given** an identity present in `.steward/keys-inventory.yaml` (Story 1.5)
**When** `steward keys revoke --scope <name>` is run
**Then** the inventory entry is marked retired (visible in a subsequent `steward keys list`)
**And** stdout prints the manual remediation steps appropriate to that identity's provenance (e.g. "rotate the upstream JFrog token; this tool cannot call JFrog's revocation API" for an `observed` entry)

**Given** no third-party provider credentials or network calls exist in this story's implementation
**When** the code is reviewed
**Then** no JFrog/GitHub/Anthropic API client import exists — revoke is a local record-and-guide action only, per the PRD's explicit v1 non-goal

---

## Epic 2: Deploy — Reconciled Dashboard Publishing

Formalize the hand-run `dashboard-gen` + push loop. Governed by AD-1, AD-4.

### Story 2.1: The dashboard builds through Steward, not a bare pixi task the operator has to remember

As the repo maintainer,
I want `steward deploy dashboard --build` to run the existing `dashboard-gen` pixi task,
So that the dashboard build step lives behind the same CLI as everything else Steward does.

**Acceptance Criteria:**

**Given** the existing `dashboard-gen` pixi task (`pixi.toml`'s `[feature.local-recipes.tasks.dashboard-gen]`)
**When** `steward deploy dashboard --build` is run
**Then** it invokes that exact task (subprocess, per AD-1 — no reimplemented generation logic) and `docs/dashboard/` reflects freshly generated output
**And** a failure in the underlying task (non-zero exit) surfaces as a clear Steward-level error, not a silent success

---

### Story 2.2: Nothing happens unless something actually changed

As the repo maintainer,
I want `steward deploy dashboard` to diff the freshly built output against the committed tree and only commit+push when there's a real difference,
So that I never wonder whether an empty commit just landed for no reason.

**Acceptance Criteria:**

**Given** a repo state where `docs/dashboard/`'s committed content already matches what a fresh build produces
**When** `steward deploy dashboard` is run twice in a row with no source changes between runs
**Then** the second (and first, if nothing changed) run results in **zero commits** — the FR-9 zero-commit-on-no-diff property, verified by asserting `git log` has no new commit after the run

**Given** a change to `docs/dashboard/generate.py`'s output between runs
**When** `steward deploy dashboard` is run
**Then** exactly one new commit is created, containing exactly the changed dashboard files, and the commit is pushed to the branch GitHub Pages already serves from (direct push, no new Actions workflow — per AD-4)

---

### Story 2.3: The operator can see what would change before it changes

As the repo maintainer,
I want `steward deploy dashboard --dry-run` to build and diff without committing or pushing,
So that I can review a dashboard change before it goes live.

**Acceptance Criteria:**

**Given** Story 2.2's build+diff logic
**When** `steward deploy dashboard --dry-run` is run against a repo state with a real pending diff
**Then** the diff is printed to stdout/stderr and **no commit or push occurs** (verified: `git log`/`git status` unchanged after the run)

**Given** a repo state with no diff
**When** `steward deploy dashboard --dry-run` is run
**Then** it reports "no diff" and exits 0

---

### Story 2.4: The operator can ask "when did the dashboard last actually deploy?"

As the repo maintainer,
I want `steward deploy status` to report the last successful dashboard deploy (commit SHA, timestamp),
So that I don't have to `git log -- docs/dashboard/` by hand.

**Acceptance Criteria:**

**Given** at least one prior deploy commit created by Story 2.2
**When** `steward deploy status` is run
**Then** it prints that commit's SHA and timestamp, read from Git history (no separate state file — per FR-11's "no separate state store" constraint)

**Given** a repo with no prior Steward-created deploy commit
**When** `steward deploy status` is run
**Then** it reports that clearly rather than crashing or printing a misleading empty result

---

## Epic 3: Provision — Environment & Runner Access

Thin CLI face over the existing pixi estate and `bmad-loop-worktree`. Governed by AD-1, AD-5.

### Story 3.1: Any named pixi environment materializes with one command

As the repo maintainer,
I want `steward provision --env <name>` to resolve `<name>` against pixi.toml's `[environments]` table and run `pixi install -e <name>`,
So that I never have to recall exact pixi invocation syntax for any of the ~14 environments.

**Acceptance Criteria:**

**Given** repo-root `pixi.toml`'s `[environments]` table
**When** `steward provision --env pyforge-atlas` is run
**Then** it shells out to `pixi install -e pyforge-atlas` (per AD-5 — no reimplemented resolution logic) and the environment materializes successfully

**Given** a name that does not exist in the `[environments]` table
**When** `steward provision --env not-a-real-env` is run
**Then** it reports a clear error listing valid environment names, rather than passing the bad name through to pixi and surfacing pixi's own raw error

**Given** this story's own dogfooding target (Additional Requirements)
**When** `steward provision --env pyforge-steward` is run
**Then** it successfully materializes Steward's own dev/test environment

---

### Story 3.2: A bmad-loop runner and its environment materialize together

As the repo maintainer (or an unattended bmad-loop session acting on my behalf),
I want `steward provision --runner bmad-loop --env <name>` to wrap `scripts/bmad-loop-worktree` and materialize a worktree + its named pixi environment in one call,
So that starting a new loop doesn't require two separate manual steps.

**Acceptance Criteria:**

**Given** Story 3.1's environment-materialization logic and the existing `scripts/bmad-loop-worktree` script
**When** `steward provision --runner bmad-loop --env <name>` is run
**Then** it invokes `scripts/bmad-loop-worktree` (subprocess, per AD-1/AD-5 — Steward never reimplements or forks worktree logic) and the named environment is materialized inside the resulting worktree

**Given** a failure in the underlying `bmad-loop-worktree` script
**When** this command is run
**Then** the failure surfaces as a clear Steward-level error, and no partial/orphaned worktree state is left silently unreported

---

### Story 3.3: The operator can see every environment that exists, before picking one

As the repo maintainer,
I want `steward provision --list` to enumerate every environment in pixi.toml's `[environments]` table with its composing features,
So that I can discover what's available instead of reading raw TOML.

**Acceptance Criteria:**

**Given** repo-root `pixi.toml`'s current `[environments]` table (~14 entries)
**When** `steward provision --list` is run
**Then** every environment name is listed with its composing `features` list, read-only (Steward never writes to `pixi.toml` — per AD-5)

**Given** `--json` is passed
**When** `steward provision --list --json` is run
**Then** the same data is emitted as machine-readable JSON

---

### Story 3.4: The environment.yaml sync gate is one command away, not a remembered incantation

As the repo maintainer,
I want `steward provision --verify` to wrap the existing `environment.yaml` ↔ `pixi.toml` sync-gate check and report drift,
So that I don't have to remember `pixi project export conda-environment -e build` and diff it by hand before every PR touching `pixi.toml`.

**Acceptance Criteria:**

**Given** the existing sync-gate check this repo's CI already enforces (CLAUDE.md § "PR CI gates")
**When** `steward provision --verify` is run against a repo state where `environment.yaml` is in sync with `pixi.toml`
**Then** it reports clean and exits 0

**Given** a repo state where `pixi.toml` changed but `environment.yaml` was not regenerated
**When** `steward provision --verify` is run
**Then** it reports drift and exits non-zero, wrapping the existing check's logic rather than reimplementing the comparison (per AD-1)

---

## Epic 4: Budget — Declared Resource Ceilings

Make the "$1500/month locked" doctrine machine-readable, conservatively. Governed by AD-1, AD-6.

### Story 4.1: A ceiling can be declared, machine-readably

As the repo maintainer,
I want `steward budget set --cap <amount><currency>/<period>` to record a machine-readable ceiling to a tracked config file,
So that "the ceiling is $1500/month" stops being a sentence in a Dream file only I remember to reread.

**Acceptance Criteria:**

**Given** `.steward/budget.yaml` (the tracked, repo-root config location)
**When** `steward budget set --cap 1500usd/month` is run
**Then** the file records the amount, currency, and period in a stable, documented schema

**Given** a malformed cap value (e.g. missing unit, unparsable amount)
**When** `steward budget set --cap garbage` is run
**Then** it reports a clear usage error and does not write a corrupt entry to the config file

---

### Story 4.2: The declared ceiling is one command away

As the repo maintainer,
I want `steward budget show` to print the currently declared ceiling(s) in human and `--json` form,
So that I can check the doctrine without opening a YAML file by hand.

**Acceptance Criteria:**

**Given** a ceiling declared via Story 4.1
**When** `steward budget show` is run
**Then** it prints the ceiling in a human-readable form
**And** `steward budget show --json` prints the same data as machine-readable JSON

**Given** no ceiling has ever been declared
**When** `steward budget show` is run
**Then** it reports that clearly (not a crash, not a misleading zero)

---

### Story 4.3: Asking "am I under budget?" never lies

As the repo maintainer,
I want `steward budget check` to report "no metered spend source configured" via a distinct exit code when there's nothing to check against, rather than fabricating a pass/fail,
So that a script calling this command can tell the difference between "no data," "under budget," and "over budget."

**Acceptance Criteria:**

**Given** no metered spend source is wired into Steward (true for all of v1 — per the PRD's explicit non-goal on Kubecost/OpenCost/Infracost-class integration)
**When** `steward budget check` is run, regardless of whether a ceiling was declared (Story 4.1)
**Then** it prints "no metered spend source configured" and exits with a dedicated, documented exit code distinct from a hypothetical future "under budget" (0) or "over budget" (non-zero-and-different) code

**Given** the codebase at the end of this story
**When** it is reviewed for imports
**Then** no cloud-cost-SDK or Kubecost/OpenCost/Infracost client import exists anywhere in `budget.py` — the honest-stub property is structural, not just behavioral

---

## Final Validation Summary

- **FR coverage:** all 18 FRs (FR-1..FR-18) map to exactly one story each (§ FR Coverage Map); FR-7 is carried as an explicit AC within Story 1.2 rather than a separate story, since it is a direct regression property of the resolver that story builds.
- **NFR coverage:** NFR-1/NFR-4/NFR-5/NFR-6/NFR-7 realized in Epic 1 (established once, reused everywhere); NFR-2 in Epic 2; NFR-3 in Epic 3.
- **Architecture compliance:** the Structural Seed's scaffold lands as Epic 1 Story 1.1 (this repo's "starter template" equivalent, per this skill's own validation rule); AD-7/AD-8 (shared `Duty` protocol, exit-code ownership) are established once in Story 1.1 and never re-decided; every story's ACs cite the AD(s) governing it.
- **Epic independence:** each epic delivers complete, standalone functionality for its duty; Epics 2-4 depend only on Epic 1's scaffold output (packaging + dispatcher + protocol), never on each other or on a future epic.
- **Within-epic story dependency:** every story within an epic depends only on prior stories in that same epic (e.g. 1.4 rotation depends on 1.3 encryption; 1.6 audit depends on 1.2's detection primitive + 1.5's inventory; 3.2 runner provisioning depends on 3.1's environment-materialization primitive) — no forward dependencies.
- **Story sizing:** each story is scoped to one CLI verb (or a tight cluster: encrypt+decrypt in 1.3) with a small, testable surface — sized for a single `bmad-quick-dev`/`bmad-dev-story` session.

## assumptions[]

- Ran headless/express; epic-structure approval and per-story review menus in the underlying skill were self-confirmed rather than presented interactively, per the calling task's directive.
- Folding the PRD's tentative "Epic E — Packaging & Test Scaffold" into Epic 1 Story 1.1 is a judgment call made per this skill's own epic-design principles (no-user-value technical-layer epics are disallowed) — flagged explicitly since it diverges from the PRD's exact tentative wording, though the PRD itself left the call open for this stage.
- Exact exit-code integer values (SIGINT code, internal-error code, budget's not-configured/under/over triad) are left for Story 1.1/4.3's implementation to fix and document — the spine's AD-8 binds the *ownership* rule, not the specific integers, which is appropriately scaffold-level detail per the architecture's own "Deferred" note on the `Duty` protocol's exact shape.

## open_questions[]

Carried forward from the PRD/architecture chain, still unresolved at story-writing granularity (none block starting Epic 1):

- Exact `.steward/budget.yaml` and `.steward/keys-inventory.yaml` schemas (field names, types) are implementation detail for Stories 1.5/4.1 to fix, not pre-decided here.
- Whether `steward keys audit --drift`'s fixture-based detection (Story 1.2/1.6) should ship as a static-analysis pattern match or something more structured (AST-based) is a Story 1.2 implementation decision, not an architecture-level one.

---

## Epic 5: The Marshal seam — obligations from the 2026-08-08 seam ratification

**Value delivered.** The two stations stop overlapping. Marshal's AD-71 named both of
these as "actioned in Steward's chain" when the build-line/estate seam was ratified;
until this epic they existed only as a claim in another station's architecture, which is
exactly the unowned-obligation shape the seam was meant to end.

### Story 5.1: Retire `provision --runner bmad-loop` in favour of `marshal init`

As the operator,
I want one command that provisions a loop home,
So that two stations do not ship two ways to make the same thing, one of them wrapping
a legacy script.

**Type:** change • **Effort:** S • **Deps:** — • **FR/AD:** AD-5 (this station), Marshal AD-71
**Surface:** `provision.py`, `cli.py`, `tests/`

**Why.** Steward's **own AD-5** already calls this "Marshal-owned machinery", and
`provision --runner bmad-loop` shells to the *legacy* `scripts/bmad-loop-worktree` while
`marshal init` (Epic 1, 10 shipped stories) is a strict superset — worktree plus the
marker↔symlink agreement invariant, the AD-11 never-write proof, and an idempotent
`done | skipped | failed` step report.

**Acceptance Criteria:**

**Given** an operator runs `steward provision --runner bmad-loop --env <name>`
**Then** it either delegates to `marshal init` or exits with a finding naming
`marshal init <slug>` as the supported path — never silently provisions via the legacy
script
**And** `--env <name>` (pixi environments, genuinely Steward's) is unaffected
**And** the removal is recorded in this station's own architecture, not only in Marshal's

**Status:** done

**Outcome (2026-08-09).** Retired by REPORTING, not delegating. Steward imports nothing
from `pyforge.marshal` and shells to no `marshal` binary; proxying the front door would
create this station's first cross-station coupling and re-wrap the very machinery the
story removes. `run_bmad_loop_worktree` and its stdout parser are **deleted** — a
retirement that leaves the old path importable is a deprecation, not a removal.
`_BMAD_LOOP_WORKTREE_RELATIVE_PATH` survives because `repo_root()` locates the monorepo
by finding that script, which is unrelated to running it. AD-5 amended in **Steward's
own** ARCHITECTURE-SPINE (the AC's explicit requirement), not only in Marshal's chain.
Suite 197 → 198.

### Story 5.2: Consume the sprint ledger; never derive story status

As the operator,
I want `steward deploy dashboard` to publish exactly what the ledger says,
So that the durable record has one writer and the publisher cannot invent a second
version of the truth.

**Type:** feature • **Effort:** XS • **Deps:** — • **FR/AD:** Marshal FR-136..FR-139, AD-71
**Surface:** `deploy.py`, `tests/`

**Why.** AD-71 makes the ledger a two-sided contract: Marshal produces it and is
accountable for its currency; Steward publishes what it says and **never derives status
itself**. The producer half shipped 2026-08-08 (the monotonic guard); the consumer half
was never written down here.

**Acceptance Criteria:**

**Given** a tracked `sprint-status-ledger.yaml`
**When** `steward deploy dashboard` runs
**Then** it reads story status from the ledger only — never from git subjects, the
Tier-3 feed, or any re-derivation
**And** a ledger that is absent or unreadable is a named refusal, not a silent fallback
**And** a test asserts `deploy.py` contains no story-status derivation of its own

**Status:** done

---

## Epic 6: Module provisioning

**Value delivered.** A BMAD module is materialized by one command instead of a
remembered installer incantation. **Sequenced before Epic 7** — `provision --module`
inside an image build only exists if the backend exists first.

### Story 6.1: `provision --module <name>`
**FR/AD:** FR-19; AD-1 (wrap, never reimplement) • **Effort:** S • **Surface:** `provision.py`, `cli.py`
**Given** a supported module name **When** `provision --module <name>` runs **Then** the
module's own installer is invoked as a subprocess and the result reported; **And** an
unknown name lists the valid ones rather than surfacing a raw tool error; **And** no
module's install logic is reimplemented here.
**Status:** done

### Story 6.2: `provision --list-modules`
**FR/AD:** FR-20 • **Effort:** XS • **Surface:** `provision.py`
**Given** any state **When** the operator lists modules **Then** each supported module is
shown with its installed state, **derived from the filesystem** rather than a
hand-maintained list (derive-don't-declare).
**Status:** done

### Story 6.3: Partial install is a named failure
**FR/AD:** FR-21; AD-7 • **Effort:** XS • **Surface:** `provision.py`, `tests/`
**Given** an installer that exits non-zero, or exits 0 leaving the module unimportable
**Then** the result is a named failure — never counted as provisioned, never silent.
**Status:** done

---

## Epic 7: The one-container Guild

**Value delivered.** The whole factory ships as one deployable boundary. **Deps: Epic 6.**
Marshal's unification research recommends two image tiers; this epic commits only to the
lean all-stations image, with the packaging tier explicitly out of scope.

### Story 7.1: One build, whole Guild
**FR/AD:** FR-22 • **Effort:** M • **Surface:** `Containerfile`, `pixi.toml`
**Given** the Containerfile **When** the image builds **Then** all eight station CLIs are
present and each answers `--version` inside the container.
**Status:** done

### Story 7.2: The repo at a fixed short path
**FR/AD:** FR-23 • **Effort:** S • **Surface:** `Containerfile`
**Given** the image **Then** the checkout sits at a path short enough to avoid the
documented `pixi-build-python` path-length panic, fixed and documented rather than
derived from the build host.
**Status:** done

### Story 7.3: Credentials never enter image layers
**FR/AD:** FR-24; AD-2, AD-3 • **Effort:** S • **Surface:** `Containerfile`, `scripts/container-gates`
**Given** a built image **Then** a build-time scan finds no secret in any layer, and the
build FAILS if one is present; **And** credentials arrive at run time only, through the
existing `keys` surface.
**Status:** done

### Story 7.4: State outlives the container
**FR/AD:** FR-25 • **Effort:** M • **Surface:** `Containerfile`, `scripts/container-gates`
**Given** loop homes, the Tier-3 store and mutable caches **Then** each resolves to a
mounted volume, and a restart loses no durable state — proven by a round-trip test, not
by inspection.
**Status:** done

### Story 7.5: The image proves itself at build time
**FR/AD:** FR-26 • **Effort:** S • **Surface:** `scripts/container-gates`
**Given** the build **Then** a smoke gate fails the BUILD — not a later run — when any
station CLI is missing, unimportable, or over its documented start-up budget.
**Status:** done

---

## Epic 8: Two boards, one truth

**Value delivered.** A card moved once shows up on the other board, with no SaaS bridge
and no human re-typing. **Greenfield** — nothing exists today.

**UNBLOCKED 2026-08-10.** Every decision this epic was waiting on is answered and the Spec
carries `open_questions: []`. `Q1`/`Q5` (an **external** board pair, which is what makes this
Steward's at all) resolved 2026-08-08; `Q2`/`Q3`/`Q4` resolved by
`architecture-jira-github-projects-sync-2026-08-09` (`status: final`) — GitHub authoritative
per-field-overridable, serverless transport on a `schedule` trigger with webhook opt-in, and
Mode B's normalized schema with its three-table control plane.

**One thing happened after that and it changes how 8.1 must be built.** Story 8.1 ran, found a
real correctness defect in AD-5's original time-based zero-loop guard, and correctly HALTed
rather than ship it: the sync point was stored as a field *on the item*, so writing it advanced
the same item's `updated_at` past the value just recorded — permanently, not for a tunable
window. AD-5 was amended (PR #390) to a **value comparison against a per-field baseline**, and
**AD-10** was added for the baseline's storage contract and lifecycle. 8.1's frozen
intent-contract was re-issued from that amendment on 2026-08-10. **Never reintroduce a timestamp
comparison on the correctness path** — `updated_at` may only select candidates under
`trigger=schedule`, never decide.

**Audit note (Phase 1 backlog-truth, 2026-08-10 —
`planning-artifacts/implementation-readiness-report-20260810.md`).** 8.1 landed (PR #397);
verdicts on the rest (post-blind-review): **8.2 and 8.3 STILL-VALID, narrowed** — both
mechanisms landed with 8.1; each story's deliverable is its demonstration test, exactly as the
frozen 8-1 spec sequenced (`spec-8-1-bidirectional-propagation.md:116-120`); 8.2's test must
also cover the non-atomic baseline-refresh failure path (`sync.py:869-880`). A stale Tier-3
`blocked` record for 8.2 predates the AD-5 amendment — clear it at loop-home preflight before
re-spin.

**RESPEC resolved (`bmad-correct-course`, 2026-08-13 —
`planning-artifacts/sprint-change-proposal-2026-08-13.md`).** The original 8.4/8.5
`NEEDS-RESPEC` verdict split into one genuine gap and one false positive. **8.4's batch
premise genuinely had no producer story** — `trigger=schedule`'s candidate enumeration (AD-2/
AD-5, already decided) was never assigned to any story, so a new Story 8.4 below builds it;
the two former 8.4/8.5 shift down to 8.5/8.6. **8.5's "frozen boundary collision" was a
misreading**: Story 8.1's own frozen spec (`spec-8-1-bidirectional-propagation.md:119-121`)
explicitly *names* Story 8.5 (now 8.6) as the table's owner when it defers building one —
there is no boundary to amend, and no architecture change was needed for either fix.

### Story 8.1: Bidirectional propagation
**FR/AD:** FR-27 • **Effort:** L • **Deps:** the three open questions
**Given** a status/assignee/link change on either board **Then** it reaches the other with
no human action on the receiving side, demonstrated against a live pair.
**Status:** done — *per its frozen spec's deliberately narrowed slice: status-field-only,
fake-transport-tested. The AC's assignee/link propagation is NOT delivered and has no owning
story (audit AF-5); the live-pair demonstration is an open coverage-debt row.*

### Story 8.2: Zero-loop guarantee
**FR/AD:** FR-28 • **Effort:** M • **Deps:** S-8.1
**Given** one human change **Then** N round-trips produce exactly ONE propagation, not N —
demonstrated by test, never asserted.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.3: Idempotent update processing

> **Intent contract re-issued 2026-08-11 (operator decision).** This story's own dev pass
> built both specified tests (314 passing), and its blind adversarial review then found the
> frozen contract itself inaccurate: it claimed the opposite-identifier redelivery "covers
> AD-9's out-of-order arrival". It does not — AD-9 rule 2 is **stale-value convergence** ("a
> late delivery about a superseded value converges to the current one rather than overwriting
> it"), while redelivering via the other identifier only proves **entry-point symmetry**. Per
> the intent_gap protocol the session reverted rather than patch its own contract, and halted.
> Resolution (operator, "relabel + add the real AD-9 rule 2 test now"): both false claims are
> corrected AND a third test is added with its own fixture — a delivery carrying a superseded
> value arrives after the pair converged on a newer one, and the engine must converge to the
> CURRENT value, writing nothing. **Nothing in the suite proves AD-9 rule 2 today.**
**FR/AD:** FR-29 • **Effort:** S • **Deps:** S-8.1
**Given** an identical payload delivered twice **Then** both systems are byte-identical to
a single delivery.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated. The "nothing in the
suite proves AD-9 rule 2" residual noted above is a real, separate test-coverage gap, not a
decomposition gap.*

### Story 8.4: The schedule trigger enumerates real candidates
**FR/AD:** FR-27 (AD-2/AD-5) • **Effort:** M • **Deps:** S-8.1
**Given** `trigger=schedule` fires **Then** every linked item whose current `updated_at`
differs from its recorded per-field baseline is selected as a candidate and reconciled through
the existing single-pair `reconcile()` engine, in one run, with no `--github-item`/
`--jira-issue` pair required per invocation.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.5: Fail loud, fail alone
**FR/AD:** FR-30 • **Effort:** XS • **Deps:** S-8.1, S-8.4
**Given** a batch containing one unlinked item **Then** every other item completes and the
unlinked one emits a named, greppable error.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.6: Explicit status-vocabulary translation
**FR/AD:** FR-31 • **Effort:** S • **Deps:** S-8.1
**Given** any status crossing the boundary **Then** it passes through a reviewable mapping;
an unmapped value is a hard logged failure, never a pass-through inventing a state.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.7: Assignee and identity-link propagation
**FR/AD:** FR-140 (spec-jira-github-projects-sync, CAP-1 residual; found undecomposed,
2026-08-15 fleet-wide decomposition audit) • **Effort:** M • **Deps:** S-8.1
**Given** a status/assignee/link change on either board **Then** the assignee and identity
link propagate to the other side too, no human action on the receiving side — the two-thirds
of CAP-1 Story 8.1's own frozen intent-contract deliberately narrowed away (status-field-only,
fake-transport-tested) and its own audit note (AF-5) named as undelivered with no owning
story until this one. Uses the same reconcile/baseline machinery Story 8.1 already
established (AD-5's value-comparison guard, AD-10's baseline contract) — never a second
propagation path.
**Status:** backlog

## Epic 9: Secure live dashboards

**Value delivered.** The reusable role-based live-dashboard pattern of
`spec-secure-live-dashboards` (ready, 8 CAPs, architecture final 2026-08-09): identity at the
ASGI boundary, declared row-isolation, role-built navigation, a see-what-was-seen audit
trail, server-gated export, a shipped perimeter, non-vacuous proof tests, and hosted-or-static
without a fork. Atlas's Vizro board is the first adopter, not the subject. ASGI stack ships as
the `pyforge-steward[dashboard]` **optional extra** per unified-container AD-1 — never a base
dependency.

> **Operator override, recorded 2026-08-10 (in-session, "steward secure-dashboard").** The
> registry's revisit condition for this Spec was *"Epic 8 completes"* — Epic 8 is **1/5** at
> authoring (8-1 done; 8-2/8-3 dispatchable; 8-4/8-5 blocked NEEDS-RESPEC). The concern was
> raised and the operator directed decomposition anyway. Consequence to schedule around: a
> steward run will interleave Epic 8's remainder with this epic; nothing here depends on
> Epic 8, so the interleave is a throughput choice, not a correctness risk.

**Companion binding.** The Spec's `ARCHITECTURE-SPINE` companion is the build contract:
AD-1 (optional extra), **AD-4** (refuse to start when identity headers arrive from outside
declared ingress), **AD-5** (no role-filtered dataset in the shared cache), **AD-6**
(API shape enforces filter-then-search), **AD-7** (retention declared, no default,
deployment refused without it), **AD-11/AD-12** (per-message isolation), **AD-14** (SQLite
dev / Postgres deploy). Each is cited by the story that owns it — an earlier draft cited
only AD-1 and was refused on review.

### Story 9.1: Identity at the boundary, declared isolation, and the cache invariant
**Type:** foundation • **Effort:** L • **Deps:** none • **FR/AD:** CAP-1, CAP-2; AD-4, AD-5, AD-14
**Surface:** ASGI middleware, adopter-declaration schema, cache layer
**Given** a request **Then** identity and role arrive from the request at the ASGI boundary
(the pattern authenticates no one) and the adopter DECLARES its access column and roles
rather than implementing filtering. **AD-4:** identity headers arriving from outside the
declared ingress refuse the start, not the request. **CAP-2's real invariant (AD-5):** two
concurrent users of different roles produce **one** upstream fetch and **a role-filtered
frame is never written back to the shared cache** — asserted by test, not documented.
**AD-14:** SQLite in dev, Postgres in deployment.

### Story 9.2: An unauthorized page is absent, not hidden
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** CAP-3; AD-6
**Surface:** navigation builder, API surface
**Given** a caller's role **Then** the navigation tree is constructed from it — a page the
user cannot access does not exist in their tree — and the API shape enforces
filter-then-search (AD-6), never search-then-filter.

### Story 9.3: The audit trail records what was seen
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** CAP-4; AD-7, AD-11, AD-12
**Surface:** audit-trail store, retention config
**Given** any data load, filter, navigation or export **Then** a durable role-isolated trail
entry records what was actually seen, not merely that an event fired; **retention is declared
with no default and deployment is refused without it** (AD-7); per-message isolation holds
(AD-11/12).

### Story 9.4: Export gated server-side
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** CAP-5
**Surface:** export endpoint
**Given** an export request **Then** authorization is enforced server-side (no client-side
gate is trusted) and the export may be encrypted.

### Story 9.5: The perimeter ships with the pattern
**Type:** infra • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** CAP-6; AD-1
**Surface:** `pyforge-steward[dashboard]` extra, deployment manifests, edge config
**Given** an adopter **Then** they receive a production-shaped runtime rather than assembling
one: Django+Channels+Daphne via the optional extra **plus the edge that terminates TLS and
enforces network policy** (CAP-6's clause an earlier draft dropped).

### Story 9.6: Isolation proven by tests that cannot pass vacuously
**Type:** test • **Effort:** L • **Deps:** S-9.2, S-9.3, S-9.4, S-9.5 • **FR/AD:** CAP-7
**Surface:** proof suite
**Given** the proof suite **Then** it impersonates distinct identities and **fails loudly if
isolation is removed** — a suite that cannot fail is a failing suite; the cache invariant
(9.1) and the retention refusal (9.3) each carry a mutation-proof case.

### Story 9.7: Hosted or static, no fork
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** CAP-8
**Surface:** static-export path
**Given** a board needing no isolation **Then** the same definition publishes as a static
GitHub-Pages site — mutually exclusive with role isolation, never a second codebase.

## Epic 10: python-agent-platform — the host takes root

**Spec binding.** Decomposes `spec-python-agent-platform` (this station's specs/ dir; all
open questions resolved 2026-08-14, operator: OCP-first with GKE as a CI portability profile;
in-repo at `src/platform/` per the monorepo goal; ship on py3.12 with py3.14 as a release
gate; Docker AND Podman with rootless Podman as the reference posture). Stories cite CAP-1..6
directly — the Spec is the contract; no new FR numbers are minted. Story 10.4 is conda-forge
feedstock work and per the repo's Rule 1 its dev session MUST invoke the
`conda-forge-expert` skill; it is the py3.14 unblocker and rides in parallel (no deps).

### Story 10.1: The host renders into src/platform
**Type:** foundation • **Effort:** L • **Deps:** none • **FR/AD:** spec-python-agent-platform CAP-1
**Surface:** `src/platform/` (new), `.github/workflows/` (platform CI, paths-filtered)
**Given** the cookiecutter-django render (parameters pinned in the story spec: root
`src/platform/`, FastAPI integration on, `env()`-split settings, PostgreSQL + Redis only)
**Then** `src/platform/manage.py check` passes against PostgreSQL + Redis with no other
infrastructure, health endpoints exist for K8s probes, static assets are vendored zero-CDN,
and platform CI runs `working-directory: src/platform` filtered on `paths: [src/platform/**]`
— factory detector jobs and platform jobs never pay for each other. The factory/platform
boundary is enforced: no `pyforge.*` import anywhere under `src/platform/` (a lint/test
asserts it).

### Story 10.2: One factory-sourced environment
**Type:** infra • **Effort:** M • **Deps:** none • **FR/AD:** spec-python-agent-platform CAP-5
**Surface:** `pixi.toml`, `environment.yaml`, `docs/reference/library-llms-full.md`, drift baseline
**Given** a new `[feature.python-agent-platform]` + env pinning `python = "3.12.*"`
env-scoped (rest of repo stays 3.14) with langflow, dbgpt, dbgpt-serve, django and host deps
from conda-forge **Then** `pixi install -e python-agent-platform` solves reproducibly, and
the SAME story owns the known env-count reconcile ripple end-to-end: `pixi project export
conda-environment -e build > environment.yaml`, llms-full catalog regeneration (new deps +
the now-uncommented `pixitainer` pin — its conda-forge feedstock exists), bmad-drift
count/doc reconcile and `python scripts/bmad_drift_check.py --write-baseline` (files
`git add`-ed BEFORE stamping). A green story leaves every detector no redder than it found it.

### Story 10.3: One image, both engines
**Type:** infra • **Effort:** L • **Deps:** S-10.1, S-10.2 • **FR/AD:** spec-python-agent-platform CAP-6
**Surface:** `src/platform/Containerfile`, `src/platform/compose/`, platform CI
**Given** a UBI-minimal-based multi-stage Containerfile whose environment layer is generated
from the pixi env **Then** the image builds under BOTH `docker build` and `podman build`
(secret mounts only via the `--mount=type=secret` form both honor; OCI manifests; no
Docker-only extensions), runs rootless (arbitrary-UID clean — the OCP `restricted-v2`
predictor), and CI exercises both engines. **Pixitainer evaluation is a named AC:** attempt
the env→layer step with `pixitainer`/`pixitainer-docker` (conda-forge feedstock available)
and record a dated verdict in the Spec — adopted for the layer, adopted dev-only, or
rejected with the reason; hand-rolled multi-stage is the fallback, not the default
assumption.

### Story 10.4: The bcrypt pin stops blocking 3.14
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** spec-python-agent-platform CAP-5 (release gate)
**Surface:** langflow-feedstock (maintainer flow), upstream langflow issue
**Given** langflow-base's `bcrypt ==4.0.1` pin (upstream main re-verified 2026-08-14, pinned
beside `passlib>=1.7.4`) **Then** two lanes run: (a) the upstream ask — an issue/PR proposing
langflow drop passlib (direct `bcrypt` or `pwdlib`); (b) the runtime-validated feedstock
loosening — `bcrypt >=4.0.1,<5` with a build-number bump whose recipe test exercises the
REAL API-key/password-hashing path under bcrypt ≥4.1 (an import check is insufficient),
via the local-mirror-first maintainer flow (edit `recipes/`, build locally, push, request
rerender). Dev session invokes `conda-forge-expert` (Rule 1). Success: a py3.14 solve of
langflow + dbgpt + django completes cleanly.

### Story 10.5: The DB-GPT sidecar image + docker-compose wiring
**Type:** infra • **Effort:** M • **Deps:** S-10.3 • **FR/AD:** spec-python-agent-platform CAP-6, AD-17
**Surface:** `src/platform/compose/dbgpt/`, platform CI
**Given** DB-GPT's Pattern-B deviation (AD-14, dated 2026-08-21 in `db-gpt-django-plugin.md`)
**Then** a `docker-compose.yml` service builds and runs DB-GPT as its own container (model
worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as
Story 10.3's image, wired into the local-dev tiers (AD-16) and platform CI so 11.2's sidecar
integration is testable end-to-end without a manual DB-GPT setup step. Added 2026-08-21 —
Story 10.3 shipped "one image, both engines" before this deviation existed; this is the
additive counterpart for the engine that no longer fits that image, not a correction to 10.3.

## Epic 11: The engines join as pluggable apps

**Spec binding.** CAP-2, CAP-3, CAP-4 and the isolation/statelessness constraints of
`spec-python-agent-platform`. Pattern A per the plugin dreams ([[langflow-django-plugin]],
[[db-gpt-django-plugin]]) is the default; a sidecar fallback requires a dated deviation in
the Dream first (AD-14) and is selected through AD-17's per-engine config switch, added
2026-08-21 after DB-GPT's Pattern-B deviation — see the 2026-08-21 sprint-change-proposal.
Langflow (11.1) is unaffected and stays on Pattern A.

### Story 11.1: Langflow joins as a pluggable app
**Type:** feature • **Effort:** L • **Deps:** S-10.1, S-10.2 • **FR/AD:** spec-python-agent-platform CAP-2
**Surface:** `src/platform/langflow_integration/`
**Given** the `langflow_integration` app **Then** an ASGI dispatcher mounts Langflow's app at
`/api/v1/`, `/health`, `/langflow/`; a `RunSQL` migration provisions `langflow_schema`;
`LANGFLOW_DATABASE_URL` carries the `search_path` suffix; no local-disk state path survives;
and a flow executes end-to-end through the mount with its tables provably confined to
`langflow_schema`.
**And** (added 2026-08-14, AD-16 — folded here rather than into 10.2, whose contract was
frozen mid-dev under the graceful stop) a `platform-dev` pixi feature exists providing
per-user `postgresql` + `pgvector` + `redis-server` (plus `kubernetes-helm`/
`kubernetes-client`) so this story's schema work — and all of Epic 11 — runs on the
guaranteed baseline with no managed services and no containers; its pixi.toml edit carries
the standard env-count reconcile ripple.

### Story 11.2: DB-GPT joins via its configured integration pattern
**Type:** feature • **Effort:** L • **Deps:** S-10.1, S-10.2, S-10.5 • **FR/AD:** spec-python-agent-platform CAP-3, AD-17
**Surface:** `src/platform/dbgpt_integration/`
**Given** the `dbgpt_integration` app configured for Pattern B (AD-17 — `dbgpt: B` in the
pattern registry, per the 2026-08-21 deviation dated in `db-gpt-django-plugin.md`) **Then** a
Django data migration provisions `dbgpt_schema` exactly as Pattern A would (Django ORM never
crosses in; DB-GPT's Alembic never touches `public`); the sidecar built by Story 10.5
(`docker-compose`-managed, its own FastAPI/AWEL process) is registered in the AD-17 pattern
registry; requests route to it via the Celery/Redis path (11.3) rather than an in-process
ASGI mount; `DBGPT_SESSION_STORAGE_TYPE=db` plus disabled local paths still apply inside the
sidecar; pgvector lives in the SAME PostgreSQL if a vector store is needed; a text-to-SQL
round-trip succeeds end-to-end through the sidecar. Rationale: `dbgpt-app` cannot co-install
with `langflow-base` in the shared environment (`fastapi` ceiling conflict) — Pattern B
avoids it entirely since `dbgpt-app` never enters the shared environment.

### Story 11.3: Async work never blocks Django
**Type:** feature • **Effort:** M • **Deps:** S-11.1, S-11.2 • **FR/AD:** spec-python-agent-platform CAP-4, AD-17
**Surface:** `src/platform/config/celery*`, worker wiring
**Given** Celery over Redis **Then** LLM/AWEL work dispatches to workers that call each
engine per its AD-17 pattern — Pattern-A engines in-process, Pattern-B engines (DB-GPT) via a
REST call to the sidecar's AWEL endpoint (never through the public edge) — the host stays
responsive under a long-running agent task, and the new failure mode (timeout / partial
result, now including a sidecar-unreachable case) is named and handled, not discovered.

### Story 11.4: Isolation and statelessness proven
**Type:** test • **Effort:** L • **Deps:** S-11.1, S-11.2 • **FR/AD:** spec-python-agent-platform CAP-2, CAP-3 (success clauses), AD-17
**Surface:** `src/platform/tests/`
**Given** the proof suite **Then** schema inspection asserts each engine's tables live only
in its schema; a container-replacement simulation covers BOTH the in-process Pattern-A case
(kill + fresh start loses no flow, no session, no state) AND the Pattern-B sidecar case (kill
+ restart the `docker-compose` service, proven against the same shared `dbgpt_schema`); and
the suite fails loudly if isolation or statelessness is removed, under either pattern — a
suite that cannot fail is a failing suite (the 9.6 discipline).

## Epic 12: Deploy anywhere, including nowhere-connected

**Spec binding.** CAP-6 and the Q1 resolution (OCP first, GKE as a CI portability profile
over a vanilla-Kubernetes core chart).

### Story 12.1: The vanilla chart with an OCP overlay
**Type:** infra • **Effort:** L • **Deps:** S-10.3 • **FR/AD:** spec-python-agent-platform CAP-1, CAP-6
**Surface:** `src/platform/deploy/`
**Given** a Helm chart of plain Deployment/Service/Ingress (or Gateway API) resources plus a
thin OCP Route overlay **Then** the platform deploys onto a namespace carrying only
PostgreSQL, Redis and the platform image; the image passes `restricted-v2` (arbitrary UID,
no root); and nothing in the core chart is OCP-specific.

### Story 12.2: GKE as a portability profile
**Type:** infra • **Effort:** S • **Deps:** S-12.1 • **FR/AD:** spec-python-agent-platform CAP-6 (portability clause)
**Surface:** platform CI
**Given** the same chart **Then** a CI smoke profile deploys it against a GKE-shaped target
(kind or equivalent) with the Ingress path — a profile, never a second implementation.

### Story 12.3: Air-gap parity is a failing check
**Type:** test • **Effort:** L • **Deps:** S-10.3, S-12.1 • **FR/AD:** spec-python-agent-platform CAP-6
**Surface:** platform CI, mirror-only channel config
**Given** a build + deploy executed with external egress blocked **Then** it succeeds
end-to-end — image from an internal/local registry, lockfile resolved from mirror-only
channels, zero CDN references in served assets, credentials via secret mounts only — and any
external reference is a FAILING check, not a warning.

## Epic 13: Scratch worktrees become one command

**Spec binding.** Decomposes `spec-scratch-worktree-lifecycle` (this station's specs/ dir;
authored 2026-08-14 from the best-evidenced dream of its batch — the hand-typed five-step
scratch-worktree ritual observed a dozen-plus times in one session's landing passes).
Deliberately deferred while the Epic 10-12 run was live (feed mutation under a live run is
the stuck-baseline failure mode); decomposed at the run's stop. Quick-dev-sized by design —
prefer `bmad-quick-dev` over a loop re-spin for these two stories if hand-picked.

### Story 13.1: Workspace verbs over git worktree
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** spec-scratch-worktree-lifecycle CAP-1, CAP-2, CAP-4, CAP-5
**Surface:** `src/shared/packages/pyforge-steward/` (workspace duty), steward CLI
**Given** `steward workspace start <slug> [--from <branch>]` (defaults `origin/main`, prints
the path, records bookkeeping), `ls` (cheap enumeration, no per-worktree subprocess), and
`clean [--merged-only]` (bmad-loop clean's archive-not-delete discipline) **Then** every verb
emits `--json`, and the own-worktrees-only rule is HARD: `ls`/`clean` never see Marshal's
loop-home worktrees (bookkeeping of what this tool created is the enforcement, backed by a
test that plants a foreign loop-home worktree and proves it invisible).

### Story 13.2: Status and the feed-mirror decision
**Type:** feature • **Effort:** S • **Deps:** S-13.1 • **FR/AD:** spec-scratch-worktree-lifecycle CAP-3 (+ its two open questions)
**Surface:** steward workspace duty
**Given** `steward workspace status [<slug>]` **Then** it pays the per-worktree git-subprocess
cost (dirty/clean, ahead/behind, merged?) that `ls` deliberately does not, and this story
RESOLVES the spec's two open questions with dated Spec Change Log entries: whether the Tier-3
feed rsync-mirror step becomes its own verb or joins `start`, and whether `workspace update`
exists at all — decisions recorded, not silently implemented.
