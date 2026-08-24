---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/console-parity-inventory.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
mode: headless-express
updated: '2026-08-24'
currency_review: "Reviewed 2026-08-24 (Canopy Phase 6 readiness) — spec-pyforge-unifying-strategy Epics 18–30 appended; verdict CONCERNS-proceed (packaging gates + lane1-serves-dw-h3 open). See planning-artifacts/implementation-readiness-report-20260824.md. Prior review 2026-08-15 (fleet-wide decomposition audit) — Story 8.7 added (FR-140, spec-jira-github-projects-sync's CAP-1 residual, previously undecomposed per Story 8.1's own AF-5 audit note); spec-pyforge-steward and spec-bmad-module-provisioning frontmatter status fields corrected (blank/stale-draft -> shipped, both fully decomposed and done). Prior review 2026-08-10 (Phase 1 backlog-truth audit) — 10 false Status lines corrected, Epic-8 audit note + 8.1 delivery note added; see planning-artifacts/implementation-readiness-report-20260810.md. Prior review 2026-08-02."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (AD-72).
epics_role: canonical
canopy_chain: pyforge-unifying-strategy
canopy_stepsCompleted: [1, 2, 3]
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
- **Story sizing:** each story is scoped to one CLI verb (or a tight cluster: encrypt+decrypt in 1.3) with a small, testable surface — sized for a single `bmad-quick-dev`/`bmad-dev-story` session (retired 6.x names; now `bmad-build`).

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
**Type:** feature • **Effort:** L • **Deps:** S-10.1, S-10.2, S-10.5 • **FR/AD:** spec-python-agent-platform CAP-3, AD-6 (bounded exception, 2026-08-21), AD-17
**Surface:** `src/platform/dbgpt_integration/`
**Given** the `dbgpt_integration` app configured for Pattern B (AD-17 — `dbgpt: B` in the
pattern registry, per the 2026-08-21 deviation dated in `db-gpt-django-plugin.md`) **Then** a
Django data migration provisions `dbgpt_schema` exactly as Pattern A would (Django ORM never
crosses in; DB-GPT's Alembic never touches `public`); the sidecar built by Story 10.5
(`docker-compose`-managed, its own FastAPI/AWEL process) is registered in the AD-17 pattern
registry; requests route to it via the Celery/Redis path (11.3) rather than an in-process
ASGI mount; pgvector lives in the SAME PostgreSQL if a vector store is needed; a text-to-SQL
round-trip succeeds end-to-end through the sidecar. **DB-GPT's own `service.web.database`
metadata store is the bounded AD-6 exception dated 2026-08-21, not `dbgpt_schema`**:
`dbgpt-app` structurally cannot use PostgreSQL for it (confirmed live — connector-type
rejection, SQLite-only migration path, MySQL-only column DDL), so it persists via the
dedicated `PersistentVolumeClaim` Story 10.5 already built and verified (two-boot persistence
test), never on ephemeral local disk. Rationale: `dbgpt-app` cannot co-install with
`langflow-base` in the shared environment (`fastapi` ceiling conflict) — Pattern B avoids it
entirely since `dbgpt-app` never enters the shared environment.

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
external reference is a FAILING check, not a warning. **Closeout consult (2026-08-22):** re-evaluate mason's parked `spec-miniforge-installer` — unpark if the air-gap run surfaces an offline-Python-distributable need beyond pixi+mirrored channels; else recommend archive-as-never-needed.

## Epic 13: Scratch worktrees become one command

**Spec binding.** Decomposes `spec-scratch-worktree-lifecycle` (this station's specs/ dir;
authored 2026-08-14 from the best-evidenced dream of its batch — the hand-typed five-step
scratch-worktree ritual observed a dozen-plus times in one session's landing passes).
Deliberately deferred while the Epic 10-12 run was live (feed mutation under a live run is
the stuck-baseline failure mode); decomposed at the run's stop. Quick-dev-sized by design —
prefer `bmad-build` over a loop re-spin for these two stories if hand-picked.

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

### Epic 13 extension (2026-08-22): the multi-repo layer — Stories 13.3–13.4

**Spec binding.** Decomposes `spec-multi-repo-workspaces` CAP-1..2 (seeded from the
sibling org's developer-workspace-management dream — pattern only, unlicensed; the
extend-vs-new decision is recorded in that spec's memlog: extend, because 13.1/13.2 are
this layer's substrate).

### Story 13.3: A repo set opens as one workspace
**Type:** feature • **Effort:** M • **Deps:** S-13.1 • **FR/AD:** spec-multi-repo-workspaces CAP-1
**Given** a declarative `[projects.<slug>]` repo set **Then** `steward workspace start
<feature>` cuts one worktree per registered repo on branch `f-<feature>` and generates a
`.code-workspace`; missing members are named, never guessed — and the registry-location
open question resolves here with a dated entry.

### Story 13.4: The set reports and tears down safely
**Type:** feature • **Effort:** S • **Deps:** S-13.3 • **FR/AD:** spec-multi-repo-workspaces CAP-2
**Given** an open workspace **Then** one command reports dirty/unpushed across the set,
removal refuses while any member is dirty (naming it), `--merged-only` honors the
archive-not-delete discipline per member, and the own-worktrees-only HARD rule holds
set-wide (loop homes invisible, test-planted).

## Epic 14: The BMAD core upgrades repeatably

**Spec binding.** Decomposes `spec-bmad-method-core-upgrade` (this station's specs/ dir;
authored 2026-08-21 from `docs/dreams/bmad-method-core-upgrade.md`, grounded in that day's
live 6.10.0→6.11.0 upgrade session — the second manual one-off, which re-hit the first's
traps). Ownership resolved 2026-08-15 in the Dream: steward owns the mutating apply half;
detection stays doctor's (shipped 10.1/10.2). The spec's `failure-modes.md` companion is
the trap catalog every story's tests draw from. Report-only for foreign-station surfaces —
steward reports, owners act.

### Story 14.1: The pre-flight diff retrodicts a real upgrade
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-method-core-upgrade CAP-1
**Surface:** `src/shared/packages/pyforge-steward/` (new upgrade duty), steward CLI
**Given** the installed `_bmad/_config/manifest.yaml` and a target bmad-method release
**Then** a report-only command lists skill adds/removes/renames (shim disposition +
`removals.txt` deletions), upstream-touched files the repo has locally modified,
`_bmad/custom/**` overrides that stop applying (the legacy-name unattended-halt trap), and
new hard prerequisites — and pointed at the 6.10.0→6.11.0 pair it retrodicts the 2026-08-21
findings (failure-modes.md traps 1–4, 9, 11) as a fixture test.

### Story 14.2: Apply is deliberate, branched, and never clobbers custom
**Type:** feature • **Effort:** M • **Deps:** S-14.1 • **FR/AD:** spec-bmad-method-core-upgrade CAP-2
**Surface:** steward upgrade duty
**Given** a clean tree and a CAP-1 report **Then** the wrapper snapshots/branches first, runs
`bmad-method install --action update -y` non-interactively (the installer stays the only
writer of `_bmad/bmm/**`/`_bmad/core/**`), refuses to start when legacy-name customization
files would halt the shims, and lands the installer diff for review — never applied blind;
`_bmad/custom/**` is byte-identical afterward or the run reports why not.

### Story 14.3: Clobbered custom surfaces are caught and re-applied
**Type:** feature • **Effort:** S • **Deps:** S-14.2 • **FR/AD:** spec-bmad-method-core-upgrade CAP-3
**Surface:** steward upgrade duty
**Given** a completed apply **Then** clobbered repo-custom surfaces are detected —
`resolve_config.py`'s multi-project layers 5/6 as the named regression case (clobbered in
BOTH manual upgrades) — and re-applied or flagged; success is `bmad-switch --current` AND a
`BMAD_ACTIVE_PROJECT` override resolving all six layers post-apply, installer `.bak`s
accounted for.

### Story 14.4: The pin fan-out is enumerated, not discovered by red tests
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-method-core-upgrade CAP-4
**Surface:** steward upgrade duty (report-only)
**Given** a version change in bmad-method or bmad-loop **Then** every known pin site is
enumerated with moved/not-moved status — root `pixi.toml` floors, marshal's pyproject +
package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed manifest and its drift-test map,
loop-home hook relays — exactly the sites the 2026-08-21 session had to touch (trap 5);
foreign-station sites are reported, never edited.

### Story 14.5: One command proves the upgrade landed
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-method-core-upgrade CAP-5
**Surface:** steward upgrade duty
**Given** any post-apply state **Then** one command runs the repo's own gates —
bmad-drift-check integrity, CFE skill meta-tests, per-loop-home `bmad-loop init` relay
refresh + `validate` — and reports a single verdict; the 2026-08-21 checklist (8/8 homes
validate clean, zero warnings) is the reproduced worked example.

## Epic 15: The bmad-suite channel is a governed product

**Spec binding.** Decomposes `spec-bmad-suite-channel-product` CAP-1..4 (Spec landed
2026-08-22 from `docs/dreams/bmad-suite-channel-product.md`; companion `install-matrix.md`
is the dual-path contract). CAP-5 (ambient drift) is doctor's — decomposed as doctor
Epic 15 the same day. Operator decisions locked at spec time: channel bmad-method
refreshed to 6.11.0 (executed 2026-08-22; conda-forge stays canonical), and the standing
always-refresh-outdated policy. **HARD boundaries:** wiring is per-module triage (WDS is
an explicit skip); publish credential-gated, before floor bumps; autotick output = 
reviewable PRs; dev recipes keep `X.Y.Z.dev0 @ sha` + G109 re-derivation.

### Story 15.1: One command reports the whole pipeline's truth
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-suite-channel-product CAP-1
**Surface:** steward duty (new), consuming existing probes (npm/GitHub queries, recipe.yaml parse, api.anaconda.org listing, pixi list, .claude/skills census)
**Given** the 13 suite packages **Then** one command reports upstream latest (npm AND
GitHub per the package's class), recipe version, channel version, installed version, and
wired-or-not — drift named per stage, each probe fail-open — and run against the
2026-08-22 baseline it reproduces the research matrix.

### Story 15.2: One command advances a stale package end-to-end
**Type:** feature • **Effort:** M • **Deps:** S-15.1 • **FR/AD:** spec-bmad-suite-channel-product CAP-2
**Surface:** steward duty; autotick extension (CFE Rule 1: the github_updater HEAD-advance
mode for commit-pinned dev recipes lands as CFE-skill work with its Rule-2 retro)
**Given** a package the truth-report names stale **Then** one command chains autotick
(tag-mode or HEAD-advance) → local build → recipe tests → channel publish → listing
verification, landing as a reviewable PR — the 2026-08-21 seven-stage hand ritual with
zero improvised steps, never auto-merged.

### Story 15.3: Five modules wire through the provisioning verb
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-suite-channel-product CAP-3
**Surface:** `src/pyforge/steward/provision.py` `_SUPPORTED_MODULES`
**Given** `{bmb}` today **Then** tea, cis, utility-skills, and manticore join (their conda
packages' installer entry points), each addition manifest-recorded, skill-name-collision-
checked, retired-ID guard + integrity meta tests green, reproducible on a fresh clone —
and WDS is recorded as a skip-decision with the upstream-deprecation citation.

### Story 15.4: The upgrade gate spot-checks one native path per class
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-channel-product CAP-4
**Surface:** install-matrix.md (the tracked contract), steward Epic 14 CAP-5 gate orbit
**Given** the seven native-method classes **Then** the verification gate exercises ≥1
cited command per class (dashboards excluded by build cost, check-by-doc), failures
reported not gating, and the matrix stays the cited source of truth.

**Epic 15 clears to dispatch on 15.1/15.3/15.4; 15.2 follows 15.1.**

### Epic 12 extension (2026-08-22): the local OCP hybrid environment — Stories 12.4–12.8

**Spec binding.** Decomposes `spec-local-ocp-hybrid-environment` CAP-1..5 (Spec landed
2026-08-22 from `docs/dreams/local-ocp-hybrid-environment.md` + the verbatim operator
intake under `docs/intake/`; companions `reconciliation-and-corrections.md` — every
STRIKE binding — and `cluster-bringup-facts.md`). Operator-locked at spec time: this
lands as an Epic 12 EXTENSION (not a new epic); the DB-GPT sidecar joins the chart now;
Redis keeps emptyDir but gains AUTH + NetworkPolicy; the internal-registry push is the
canonical image path. 12.2 (GKE) and 12.3 (air-gap) are unchanged; 12.3 gains sidecar
coverage for free once 12.5 lands.

### Story 12.4: The cluster bring-up is documented, reproducible, and key-disciplined
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-local-ocp-hybrid-environment CAP-1 (mints the OpenShift/registry-posture AD the steward spine anticipates)
**Surface:** `src/platform/deploy/` docs, steward keys inventory, new bring-up doc
**Given** a fresh workstation (CRC 2.63.0 / OpenShift 4.22.7 baseline; 4 cores/10.5 GB/35 GB;
Linux needs `crc` on PATH — the repo's own `openshift-client`/`podman-desktop` recipes
apply) **Then** the documented flow reaches cluster Running + `oc` authenticated + the
platform image pushed via the internal registry into an ImageStream, with pull secret,
kubeadmin credentials, and the PAT recorded as hand-authored keys-inventory entries —
zero improvised steps.

### Story 12.5: The DB-GPT sidecar joins the chart
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-local-ocp-hybrid-environment CAP-2 (closes the Epic-12-kickoff follow-up 12.1 bound out)
**Surface:** `src/platform/deploy/charts/platform/`, `tests/test_chart_invariants.py`
**Given** the platform's own sidecar image **Then** the chart renders a sidecar
Deployment (replicas 1, Recreate) + dedicated SQLite PVC at the resolved metadata path +
internal-only Service consumed via `DBGPT_SIDECAR_BASE_URL`, all under restricted-v2 —
and 12.1's inventory-test sidecar REJECTION flips to expectation, suite green.

### Story 12.6: Redis is hardened, still ephemeral
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-local-ocp-hybrid-environment CAP-3 (closes 12.1's named unauthenticated-Redis follow-up)
**Surface:** chart templates + invariant tests
**Given** the chart's emptyDir Redis **Then** AUTH arrives via an `existingSecret` key
wired into `REDIS_URL`, and a NetworkPolicy restricts Redis to platform pods — both
render-asserted; persistence deliberately unchanged (Celery re-queues).

### Story 12.7: The 12.1 Tier-3 items are verified on the live cluster
**Type:** verification • **Effort:** M • **Deps:** S-12.4, S-12.5, S-12.6 • **FR/AD:** spec-local-ocp-hybrid-environment CAP-4
**Surface:** attended run + a dated verification record in the 12.1 spec's orbit
**Given** `helm install` of core + OCP overlay on the running cluster **Then** the four
honestly-unverified items are proven — Route admission, SCC enforcement, PVC binding,
official postgres/redis images under an SCC-assigned arbitrary UID (contingency ladder:
dataMountPath/UID seams → RH images → bitnami, whichever was needed gets recorded) —
plus the fresh-install migration-window observation; failures land as findings, never
silent notes.

### Story 12.8: GitHub Projects V2 lands in github_metrics via dlt
**Type:** feature • **Effort:** M • **Deps:** S-12.4 • **FR/AD:** spec-local-ocp-hybrid-environment CAP-5
**Surface:** new small dlt pipeline (pixi workspace), board + `gh project link`
**Given** a classic PAT with `read:project` (fine-grained PATs cannot reach user-owned
projects) **Then** a custom dlt GraphQL source (no verified source covers Projects V2;
reuse `steward/sync.py`'s queries) loads items/fields/status into the `github_metrics`
dataset on cluster Postgres via port-forward, within the 5,000-points/hr budget — the
board created and repo-linked, queryable end to end; kin-declared to
`spec-jira-github-projects-sync` Mode B, never a second sync engine.

**Stories 12.4–12.6 and 12.8 clear to dispatch (12.8 after 12.4); 12.7 follows all three chart/bring-up stories. Story 12.9 (OCP portability profile) is dispatchable after 12.1+12.2; it does not replace 12.7.**

**Spec binding (2026-08-24).** Story 12.9 decomposes `spec-ocp-as-a-portability-profile` CAP-1..3
(chain Spec landed 2026-08-24 from `docs/dreams/ocp-as-a-portability-profile.md`; INV-1 requires
the folder `spec-ocp-as-a-portability-profile/`, not a `spec-12-9-*` story-spec name). Parent
`spec-python-agent-platform` CAP-6 / AD-11 remain. Adopted companions: `cluster-bringup-facts.md`,
`spec-12-2-gke-as-a-portability-profile.md`. Runner class is an open question at story time.
Ledger previously marked 12.9 done with no `ocp-portability-smoke` job — flipped to backlog.

### Story 12.9: OCP as a portability profile
**Type:** infra • **Effort:** M • **Deps:** S-12.1, S-12.2 (pattern) • **FR/AD:** spec-ocp-as-a-portability-profile CAP-1, CAP-2, CAP-3 (parent CAP-6 / AD-11)
**Surface:** platform CI (`.github/workflows/platform-ci.yml`), `deploy/README.md` honesty line
**Given** the Story 12.1 OCP overlay and a real OpenShift API (CRC / OpenShift Local — not `kind`)
**Then** an optional Platform CI job (`ocp-portability-smoke`, default off) pushes the shared
platform image via the internal-registry pattern, installs core + overlay, and curls through an
admitted Route — proving SCC-assigned UIDs and the OCP edge path end-to-end; consumes
`cluster-bringup-facts.md` registry commands, does not replace Story 12.7 attended closeout.

## Epic 16: The platform host earns its 15 factors

**Spec binding.** Decomposes `spec-platform-fifteen-factors` CAP-1..5 (seeded 2026-08-22
from the seven-repo external analysis; MIT reference implementations
django-15-factor-base + devinfra — borrow with notices; intake report carries the
inventory). **HARD:** AD-4/AD-17 topology and the 12.1 chart contract untouched — factors
land as seams, not rewrites.

### Story 16.1: Dependencies are pixi-sourced, single-authority
**Type:** chore • **Effort:** M • **Deps:** — • **FR/AD:** spec-platform-fifteen-factors CAP-5
**Given** `src/platform/requirements/*.txt` **Then** pixi.toml (the existing platform
features) becomes the sole dependency authority — CI lanes and both Containerfiles build
from pixi alone, requirements files retired, docs updated; suites green.

### Story 16.2: Startup refuses misconfiguration, two-stage and named
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-platform-fifteen-factors CAP-3
**Given** a missing/invalid required setting **Then** boot fails fast in a validation
stage that names the setting and its remedy before any app import side effects —
fixture-proven for each required key.

### Story 16.3: Every process speaks structlog + OTel
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-platform-fifteen-factors CAP-2
**Given** a request that fans into Celery **Then** structured logs carry request_id/
user_id/trace_id across web and worker, OTLP export activates only when the endpoint is
configured, and one trace correlates the hop end-to-end — asserted in tests.

### Story 16.4: Policy is a test suite
**Type:** feature • **Effort:** S • **Deps:** 16.1 • **FR/AD:** spec-platform-fifteen-factors CAP-4
**Given** the dependency/credential-surface/typing/coverage policies **Then** each is an
executable test that reds on drift (the 15-factor repo's policy-suite pattern) — wired
into the platform CI lanes.

### Story 16.5: Identity is OIDC-delegated, no local passwords
**Type:** feature • **Effort:** L • **Deps:** 16.2 • **FR/AD:** spec-platform-fifteen-factors CAP-1
**Given** a Keycloak realm-as-code local substrate (devinfra pattern: aud+roles claims,
reimport round-trip) **Then** identity keys on `idp_subject`, staff/superuser derive from
IdP group claims per-authentication (unmatched groups ignored-and-logged), local
passwords and the createsuperuser doc-path retire, and a local-dev persona/JWT minting
path exists — end-to-end login proven locally.

**Epic 16 clears to dispatch on 16.1/16.2/16.3; 16.4 after 16.1; 16.5 after 16.2.**

## Epic 17: A fresh machine reaches validate-fast through steward verbs

**Spec binding.** Decomposes `spec-developer-machine-bootstrap` CAP-1 (seeded 2026-08-22;
the sibling org's command surface as pattern only). Consumes provision --env/--runner,
the 12.4 bring-up, and Epic 16's substrate — never duplicates them.

### Story 17.1: steward init/shell-init detect and prepare the machine
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-developer-machine-bootstrap CAP-1
**Given** a machine with unknown tooling **Then** `steward init` reports each prereq
(pixi/git/gh/podman + floors from the pixi version registry) with a named remedy, and
`shell-init` emits PATH/completions/env — both idempotent, `--json` for automation.

### Story 17.2: steward setup/initrepo take the machine to green
**Type:** feature • **Effort:** M • **Deps:** S-17.1 • **FR/AD:** spec-developer-machine-bootstrap CAP-1
**Given** a passing `init` **Then** `setup` clones + pixi-installs + wires hooks and
`initrepo` onboards a repo, ending at validate-fast passing — proven in a clean
container, zero improvised steps.

---

# Chain: pyforge-unifying-strategy (Epics 18–30)

Headless/express 2026-08-24. Steward ledger already occupies Epics 1–17; this chain **appends**. Cite **parent AD-n** (python-agent-platform) vs **canopy AD-n** (unifying-strategy spine). Packaging FRs are **blocked on the operator** (canopy AD-16) — not sized as recipe stories. Phase 5 (`bmad-correct-course` × 8, Marshal retires `spec-factory-console`) is **not** an epic. Open question `lane1-serves-dw-h3` stays out of stories.

## Requirements Inventory (Canopy)

### Functional Requirements

FR-1: Chrome is installable and singular — one `django-pyforge` package; portals do not ship chrome copies. **CAP-1.**
FR-2: A portal registers itself without host URLconf/settings edits beyond what the portal supplies. **CAP-1, CAP-3.**
FR-3: App switcher shows only stations the signed-in user may reach; enforcement stays on the station. **CAP-1, CAP-12.**
FR-4: CMS page edits are live with no deploy or pod restart. **CAP-2.**
FR-5: Wagtail admin is IdP-only; no local password form; unmapped groups are refused with a clear error. **CAP-2, CAP-12.**
FR-6: Console parity inventoried before removal. **CAP-2. Satisfied 2026-08-24** (`console-parity-inventory.md`).
FR-7: Old console build path is deleted (generator, pixi tasks, workflow, data blob, inbound refs); Kedro-Viz survives; `spec-factory-console` superseded. **CAP-2.**
FR-8: Lane 1 media/renditions work across replicas; no pod-local Lane 1 state. **CAP-2.**
FR-9: All eight portals resolve same-origin, one session, under `/stations/<name>/`. **CAP-3.**
FR-9a: `/compliance/` permanent redirect to `/stations/warden/` preserving path and query. **CAP-3.**
FR-9b: Reusable-app triple; warden becomes `django-warden` / `django_warden_fabric` / `warden_fabric` before CAP-9. **CAP-3.**
FR-10: Portals render and dispatch; no station internals; no raw HTTP to services. **CAP-3, CAP-6.**
FR-11: Eight current-spec MCP faces on host ASGI; dual-era `2025-03-26`–`2026-07-28`; echo client revision; no UA branch. **CAP-4.**
FR-12: Long work is `start`/`get` over PostgreSQL; any replica serves `get`; opaque TTL handles. **CAP-4.**
FR-13: `pyforge <station> <noun> <verb>` parity with station binaries; CI fails on drift. **CAP-5.**
FR-14: Services verify audience-bound signed assertions. **CAP-6.**
FR-15: No trusted-header identity path. **CAP-6.**
FR-16: Two roles, same board URL, different rows via existing secure-dashboard pattern. **CAP-7.**
FR-17: Events durable; consumer restart does not drop or double-apply. **CAP-8.**
FR-18: Poisoned events go to DLQ, do not block the group. **CAP-8, CAP-10.**
FR-19: Cyclic publish halts at declared depth. **CAP-8.**
FR-20: Payload validation in domain adapters, not at the stream boundary. **CAP-8.**
FR-21: Liquibase ≥5.0.4 with vendored PostgreSQL JDBC on the platform channel. **CAP-9. Operator packaging.**
FR-21a: `preserveSchemaCase` off; Job connects directly with schema on the connection. **CAP-9.**
FR-22: App role cannot DDL; migration role can. **CAP-9.**
FR-23: Model change without a changeset fails CI. **CAP-9.**
FR-24: Helm Job weight −1 then `migrate --fake`; no init container. **CAP-9.**
FR-25: Test databases still use Django `migrate`. **CAP-9.**
FR-26: Circuit breaker degrades the caller; async path trips. **CAP-10.**
FR-27: Single writer for atlas DuckDB. **CAP-10.**
FR-28: Validation errors render inline. **CAP-10.**
FR-29: Restart reconciles, does not duplicate. **CAP-10, CAP-8.**
FR-30: Cache eviction loses no queued task; web and workers scale independently. **CAP-11.**
FR-31: IdP role revoke takes effect on the next request. **CAP-12.**
FR-32: No secret *value* in rendered pod specs. **CAP-12.**
FR-33: OpenFeature + cachebox 5.x on the channel. **CAP-13. Operator packaging.**
FR-34: One flag flips Django, MCP, and CLI with no egress and no redeploy. **CAP-13.**
FR-35: Scribe graph operations pass on durable PG and local drivers. **CAP-14.**
FR-36: Semantic recall returns a result lexical overlap misses. **CAP-14.**
FR-37: Each station has a SKF domain skill; proven on a station that has none today. **CAP-15.**
FR-38: Each station persona acts only through FR-13 and FR-11. **CAP-16.**
FR-39: Five-tier completeness is a failing check. **CAP-15, CAP-16.**
FR-40: Front door queries run state from a supervisor, never an operator home directory. **CAP-17.**
FR-41: Completed-run timing is ingested at completion into durable storage. **CAP-17.**
FR-42: Unreachable supervisor is explicit unavailable plus age, within FR-26 budget. **CAP-17, CAP-10.**

### NonFunctional Requirements

NFR-C1: Air-gap — Python/pixi from conda-forge; egress-blocked build is a gate.
NFR-C2: Backing services are PostgreSQL + Redis + Kubernetes only (parent AD-1). Lane 1 media is RWX, not MinIO.
NFR-C3: Stateless pods; replicas are capacity (parent AD-6).
NFR-C4: Django `>=5.2.15,<6`, Python `3.12.*`. Pin move to 5.2.17 is operator maintenance, not chain scope.
NFR-C5: `src/platform/` never imports `pyforge.*` (parent AD-2).
NFR-C6: Long-lived responses keep alive well under 30s; route annotation is not the mechanism.
NFR-C7: Search is PostgreSQL FTS; Wagtail work is Celery, not django-tasks DB/RQ / `django-tasks-celery`.

### Additional Requirements (Architecture)

- Modular monolith: one ASGI process; MCP is a URL pattern, not a roster (canopy AD-1, AD-5, AD-10).
- Citation: `parent AD-n` vs `canopy AD-n`; bare `AD-n` is review-blocking.
- JWT: RS256; claims `sub`/`roles`/`aud=mcp:<station>`/`exp`≤5m/`delegated_by=pyforge-host` (canopy AD-7). HMAC rejected.
- Events: `pyforge.events` + `pyforge.events.dlq`; `pyforgeloopdepth` ceiling 8 (canopy AD-8).
- Four PostgreSQL schemas only; `run_state`/`mcp_handles` are tables in `public` (canopy AD-9).
- Flags: in-process FILE watches the ConfigMap; Reloader/flagd sidecar is parent AD-14 (canopy AD-11).
- `start_*` is a supervisor publish (canopy AD-12).
- CAP-7 consumes `pyforge.steward.dashboard` only (canopy AD-20).
- Portal models are projections; factory package is the writer (canopy AD-18).
- CAP-15 skills are SKF content skills; CAP-16 are BMAD launcher skills; `conda-forge-expert` stays hand-authored (canopy AD-17).
- FR-9b before any CAP-9 story that revokes app-role DDL.

### UX Design Requirements

Not applicable — no `bmad-ux` contract for this chain. Chrome is `django-pyforge`; Lane 1 is Wagtail; boards consume `spec-secure-live-dashboards`.

### FR Coverage Map (Canopy)

FR-1: Epic 18 — chrome package
FR-2: Epic 18 — registration protocol
FR-3: Epic 18 — role-filtered switcher
FR-4: Epic 20 — CMS publish without deploy
FR-5: Epic 20 — Wagtail admin via IdP
FR-6: Epic 30 — inventory already done; cutover precondition
FR-7: Epic 30 — console removal
FR-8: Epic 20 — RWX media + redis-cache renditions
FR-9: Epic 19 — eight portals
FR-9a: Epic 19 — `/compliance/` redirect
FR-9b: Epic 19 — reusable-app triple (before Epic 27)
FR-10: Epic 19 — portals are projections
FR-11: Epic 21 — MCP faces
FR-12: Epic 21 — `start`/`get`
FR-13: Epic 22 — unified CLI
FR-14: Epic 18 — assertion client
FR-15: Epic 18 — no trusted headers
FR-16: Epic 23 — secure-dashboard boards
FR-17: Epic 24 — durable events
FR-18: Epic 24 — DLQ
FR-19: Epic 24 — loop-depth ceiling
FR-20: Epic 24 — adapter validation
FR-21: Epic 27 — blocked operator packaging
FR-21a: Epic 27 — schema targeting
FR-22: Epic 27 — app role DML-only
FR-23: Epic 27 — sqlmigrate gate
FR-24: Epic 27 — Helm Job −1
FR-25: Epic 27 — test DB carve-out
FR-26: Epic 25 — circuit breaker
FR-27: Epic 25 — DuckDB writer
FR-28: Epic 25 — inline validation
FR-29: Epic 25 — restart reconcile
FR-30: Epic 20 — redis-cache ≠ redis-broker
FR-31: Epic 26 — IdP revoke on next request
FR-32: Epic 26 — secret refs not values
FR-33: Epic 26 — blocked operator packaging
FR-34: Epic 26 — FILE flags, no redeploy
FR-35: Epic 28 — Scribe dual driver
FR-36: Epic 28 — semantic recall
FR-37: Epic 29 — SKF skills
FR-38: Epic 29 — personas
FR-39: Epic 29 — five-tier check
FR-40: Epic 21 — supervisor query
FR-41: Epic 21 — timing ingest
FR-42: Epic 21 — supervisor degrade

## Epic List (Canopy)

### Epic 18: Chrome and the trusted client
An operator sees one estate chrome, and every portal-to-service call carries a verifiable user.
**FRs covered:** FR-1, FR-2, FR-3, FR-14, FR-15

### Epic 19: Eight portals, one prefix
All eight stations are same-origin under `/stations/<name>/`; warden's old URL still works.
**FRs covered:** FR-9, FR-9a, FR-9b, FR-10

### Epic 20: The published front door
Editors publish at `/` without a deploy; media survives replicas; cache eviction cannot drop tasks; admin is IdP-only.
**FRs covered:** FR-4, FR-5, FR-8, FR-30

### Epic 21: Agents survive; run state is a service
Agents reconnect to in-flight work; the front door queries runs from PostgreSQL, never a laptop disk.
**FRs covered:** FR-11, FR-12, FR-40, FR-41, FR-42

### Epic 22: One command grammar
`pyforge <station> <noun> <verb>` reaches every station verb the native binary does.
**FRs covered:** FR-13

### Epic 23: Boards show only your rows
Two roles hit the same board URL and receive different rows through the estate pattern.
**FRs covered:** FR-16

### Epic 24: Stations tell each other things
Stations publish CloudEvents that survive poison and cycles, on redis-broker.
**FRs covered:** FR-17, FR-18, FR-19, FR-20

### Epic 25: Failure stays contained
A dead dependency degrades; DuckDB has one writer; validation is inline; restarts do not double-apply.
**FRs covered:** FR-26, FR-27, FR-28, FR-29

### Epic 26: Access, secrets, and flags
Revoking a role works on the next request; manifests hold refs not values; one flag flips three surfaces.
**FRs covered:** FR-31, FR-32, FR-33 (blocked), FR-34

### Epic 27: Schema change is governed
Production DDL is Liquibase under a migration role; the app cannot ALTER; tests still `migrate`.
**FRs covered:** FR-21 (blocked), FR-21a, FR-22, FR-23, FR-24, FR-25

### Epic 28: Scribe's graph outlives a file
The graph port runs on PostgreSQL/pgvector and still has a local path; recall is semantic.
**FRs covered:** FR-35, FR-36

### Epic 29: Every station is five tiers
CLI, portal, service, SKF skill, and persona exist, and a check fails when any is missing.
**FRs covered:** FR-37, FR-38, FR-39

### Epic 30: The old console is gone
After parity (including supervisor-backed run state), the generator and its inbound refs are deleted.
**FRs covered:** FR-6 (precondition), FR-7

## Epic 18: Chrome and the trusted client

An operator installs one package and every portal looks like the estate. Services independently verify who called them. Lands in `django-pyforge` (canopy AD-1, AD-3, AD-7). No `pyforge.*` import under `src/platform/` (parent AD-2).

### Story 18.1: django-pyforge is the only chrome

As a portal author,
I want one installable chrome package with an AppConfig registration protocol,
So that adding a station does not edit the host URLconf or ship a second switcher.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** FR-1, FR-2 • canopy AD-1, AD-3
**Given** two portal apps in `INSTALLED_APPS` **When** they render a page **Then** chrome markup is byte-identical and sourced from `django-pyforge`
**And** a test that enumerates portal template/static dirs **fails** if either ships a base layout, switcher, or theme copy
**And** discovery is `apps.get_app_configs()`; host URLconf has no station roster except the later `/compliance/` redirect
**And** a portal registering outside `/stations/<name>/` fails the check
**And** removing `django-pyforge` from `INSTALLED_APPS` breaks both portals identically

### Story 18.2: The switcher shows only what the user may reach

As a signed-in operator,
I want the app switcher to list only stations my IdP roles permit,
So that I am not offered doors I cannot open.

**Type:** feature • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** FR-3 • canopy AD-15
**Given** a user lacking a station role **When** they load chrome **Then** that station is absent from the switcher
**And** requesting the hidden station URL directly is still refused by that station (switcher is not enforcement)
**And** roles are re-read from the token on the request, not a durable local grant

### Story 18.3: Two clients, one RS256 assertion

As a station service,
I want every portal and CLI call to carry the same audience-bound JWT,
So that I can verify the end user without trusting a header.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** FR-14, FR-15 • canopy AD-7
**Given** the golden vector in `django-pyforge` **When** both the portal client and `pyforge.core` client emit a token **Then** both pass the same RS256 verification (`sub`, `roles`, `aud=mcp:<station>`, `exp`≤5m from `iat`, `delegated_by=pyforge-host`)
**And** a call with a bad signature, wrong audience, or expired `exp` is refused
**And** a request with an identity header and no valid assertion is refused
**And** HMAC-SHA256 and laptop-minted secrets are absent
**And** a portal constructing a raw HTTP request to a service is a review-blocking finding

## Epic 19: Eight portals, one prefix

Operators move between stations without changing origin. Warden relocates before Liquibase revokes app-role DDL (FR-9b sequencing).

### Story 19.1: Warden moves and is renamed

As a compliance auditor,
I want Warden at `/stations/warden/` with `/compliance/` still working,
So that bookmarks survive the uniform prefix.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** FR-9a, FR-9b • canopy AD-2, AD-4
**Given** the shipped `compliance_face` **When** this story merges **Then** distribution is `django-warden`, module `django_warden_fabric`, label `warden_fabric`
**And** `/compliance/` is a permanent redirect to `/stations/warden/` preserving path and query
**And** no identifier `compliance_face` remains under `src/`
**And** existing job rows, `django_migrations`, and content types survive the app-label migration
**And** this story completes **before** any Epic 27 story that revokes app-role DDL
**And** pyforge-warden planning artifacts that named the old app still resolve

### Story 19.2: Seven more portal shells under the prefix

As a platform operator,
I want every station reachable at `/stations/<name>/` in one session,
So that I do not re-authenticate to change tools.

**Type:** feature • **Effort:** L • **Deps:** S-19.1, S-18.3 • **FR/AD:** FR-9, FR-10 • canopy AD-2, AD-18
**Given** chrome and the assertion client **When** I request each of the eight portals in one session **Then** none re-authenticate and all are same-origin with Lane 1
**And** each remaining station has `django-<station>/` with the naming triple; existing models do not move between apps
**And** portals reach stations only through `django-pyforge`'s client; no portal imports station internals or builds raw HTTP to a service
**And** portal Django models are projections, not a second write path

## Epic 20: The published front door

Wagtail at `/` supersedes the static console *as the front door*; removal of the old pipeline is Epic 30.

### Story 20.1: Wagtail publishes without a deploy

As an editor,
I want to change a page and have it live without a rollout,
So that runbooks do not wait on a deploy.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** FR-4, FR-5 • canopy AD-13
**Given** an authenticated editor with the Wagtail-admin IdP group **When** they publish a page **Then** an estate request sees it with no new image and no Deployment rollout
**And** content survives pod restart and is identical from every replica
**And** unauthenticated admin requests redirect to the IdP; no local password or email-management surface is reachable
**And** an authenticated user with no admin group is refused with a comprehensible error

### Story 20.2: Media, renditions, and a cache that cannot eat the queue

As an operator,
I want uploaded media on shared storage and a cache that cannot evict Celery,
So that scaling Lane 1 does not lose files or drop builds.

**Type:** feature • **Effort:** L • **Deps:** S-20.1 • **FR/AD:** FR-8, FR-30 • canopy AD-13, AD-10 • NFR-C7
**Given** a ReadWriteMany PVC for Wagtail media and two Redis Deployments **When** replica A stores an upload **Then** replica B retrieves it
**And** a rendition generated on A is served from redis-cache by B without regeneration
**And** filling redis-cache to eviction loses no queued task on redis-broker
**And** Celery and Channels use the broker; Django cache + Wagtail renditions use the cache
**And** independent scale of work is a Celery worker Deployment — not a second public ASGI process
**And** no Lane 1 state lives on ephemeral pod disk; MinIO/S3 is a review-blocking finding
**And** search is PostgreSQL FTS; Wagtail background work uses in-tree Celery `BaseTaskBackend` (not django-tasks DB/RQ, not `django-tasks-celery`)

## Epic 21: Agents survive; run state is a service

`start_*` is a supervisor publish (canopy AD-12). Handles live in `public.mcp_handles`; runs in `public.run_state`.

### Story 21.1: Supervisor tables in public

As an agent,
I want handles and run rows in PostgreSQL owned by `django-pyforge`,
So that any replica can answer `get` and the front door never reads a laptop disk.

**Type:** feature • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** FR-12, FR-40 • canopy AD-6, AD-9, AD-12
**Given** the platform database **When** this story lands **Then** `run_state` and `mcp_handles` exist as tables in `public`, not new schemas
**And** DDL is authored as Django migrations owned by `django-pyforge` (Epic 27 will extract changesets)
**And** no front-door or MCP path reads `~/.bmad-loops`, tmux, or journals

### Story 21.2: Atlas MCP on the host, dual-era

As an autonomous agent,
I want atlas's service face on `POST /stations/atlas/mcp` using the official `mcp` SDK,
So that handshake-era and modern clients both work.

**Type:** feature • **Effort:** L • **Deps:** S-18.1, S-18.3 • **FR/AD:** FR-11 • canopy AD-5
**Given** the host ASGI process **When** a client posts to `/stations/atlas/mcp` **Then** the face speaks MCP revisions `2025-03-26` through `2026-07-28`
**And** handshake `initialize` echoes the client's requested revision; unsupported revisions return `-32022` with the supported list
**And** no code path branches on client name or user-agent; deprecated dual-endpoint SSE is not served
**And** atlas's existing server is brought to this spec, not duplicated
**And** the `local-recipes` stopgap (`fastmcp>=3.4.7,<4` + `mcp>=1.24,<2.0`) lifts its `mcp` ceiling in this story if the platform env can take `mcp>=2.0`

### Story 21.3: start/get survives disconnect

As an autonomous agent,
I want a multi-minute operation to return a handle immediately and be fetchable after a drop,
So that a 30s idle timeout does not lose the work.

**Type:** feature • **Effort:** L • **Deps:** S-21.1, S-21.2 • **FR/AD:** FR-12 • canopy AD-6, AD-12
**Given** a simulated ingress disconnect mid-operation **When** the client reconnects with the handle and a valid assertion **Then** it receives the same result without recomputation
**And** `start_*` returns before the work finishes and publishes through the supervisor (no second ledger)
**And** `get_*` succeeds on a different replica; possession of the handle without the assertion is refused
**And** handles are opaque, high-entropy, and TTL'd; progress notifications / sticky sessions / stream replay are not the survival mechanism

### Story 21.4: The other seven MCP faces

As an autonomous agent,
I want every station on the same POST pattern,
So that I do not learn eight transports.

**Type:** feature • **Effort:** L • **Deps:** S-21.3 • **FR/AD:** FR-11 • canopy AD-1, AD-5
**Given** the atlas face **When** the remaining seven stations register MCP tokens **Then** `POST /stations/<name>/mcp` conforms to the same dual-era checks
**And** host dispatch is a pattern, not a per-station list

### Story 21.5: Front door queries the supervisor

As a platform operator,
I want live runs and completed timing from the supervisor,
So that the published board is not `unavailable` for lack of my home directory.

**Type:** feature • **Effort:** M • **Deps:** S-21.1 • **FR/AD:** FR-40, FR-41, FR-42 • canopy AD-12, AD-15
**Given** a deployed egress-blocked namespace **When** the front door renders run state **Then** it uses the supervisor API only — no filesystem fallback
**And** a run started on one machine is visible to a front door on another
**And** timing is ingested at run completion, queryable across runs
**And** an unreachable supervisor renders explicit unavailable plus age, within the FR-26 budget — not an empty list presented as current

## Epic 22: One command grammar

### Story 22.1: pyforge dispatches without reimplementing

As a packaging engineer,
I want `pyforge <station> <noun> <verb>` to match each station binary,
So that I do not memorize eight CLIs.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** FR-13 • canopy AD-14
**Given** the eight station console scripts **When** CI generates the parity matrix **Then** every verb is reachable through both paths
**And** adding a station verb that the unified entry cannot reach fails the build
**And** no station logic is copied into `pyforge-core`; dispatch only
**And** a station CLI that cannot be introspected gets a named preparatory story rather than a silent skip

## Epic 23: Boards show only your rows

### Story 23.1: Same URL, different rows

As a compliance auditor,
I want analytical boards behind the host to filter rows by my role,
So that I never see another tenant's slice.

**Type:** feature • **Effort:** L • **Deps:** S-18.2, S-19.2 • **FR/AD:** FR-16 • canopy AD-20
**Given** two authenticated users with different roles **When** they request the same board URL **Then** returned rows differ as their roles dictate
**And** isolation is `pyforge.steward.dashboard` filter-then-search (`filter_by_role` / `AccessDeclaration`), server-side
**And** a second isolation stack (including Vizro that filters its own rows) is a review-blocking finding
**And** atlas's own Vizro CLI pages stay outside the host (non-goal)

## Epic 24: Stations tell each other things

Events ride redis-broker from Story 20.2. This epic does not re-split Redis.

### Story 24.1: CloudEvents on redis-broker

As a station,
I want durable events with a DLQ,
So that a poison payload cannot stall the group.

**Type:** feature • **Effort:** L • **Deps:** S-20.2 • **FR/AD:** FR-17, FR-18 • canopy AD-8
**Given** a consumer that is down **When** an event is `XADD`ed to `pyforge.events` **Then** it is delivered on return without double-apply
**And** a malformed event lands in `pyforge.events.dlq` via `XAUTOCLAIM` and does not block the group
**And** an operator can enumerate quarantined messages
**And** producers never write to redis-cache; `dataschema` is required

### Story 24.2: Cascades halt; adapters validate

As a platform operator,
I want cyclic fan-out to stop at depth 8,
So that a buggy producer cannot run away.

**Type:** feature • **Effort:** M • **Deps:** S-24.1 • **FR/AD:** FR-19, FR-20 • canopy AD-8
**Given** a deliberate cycle **When** `pyforgeloopdepth` reaches 8 **Then** publish halts observably
**And** event `type` is a dotted verb registered in `django-pyforge`
**And** payload shape is rejected in the consuming domain adapter, not at the stream boundary

## Epic 25: Failure stays contained

Each invariant has a test that fails with the mechanism absent (canopy AD-15).

### Story 25.1: Circuits trip on async too

As an operator,
I want a dead dependency to degrade the caller,
So that one outage does not hang the estate.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** FR-26 • canopy AD-15
**Given** repeated outbound failures **When** the circuit opens **Then** the caller returns degraded within budget
**And** a failing asyncio call registers as a failure (in-tree PyBreaker wrapper), not a success
**And** `fail_max` is coarse, never exact-count
**And** removing the wrapper makes the test fail

### Story 25.2: One DuckDB writer

As an atlas consumer,
I want a single writer on `atlas.duckdb`,
So that concurrent connects cannot corrupt it.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** FR-27 • resilience BS-5
**Given** a live `atlas.duckdb` **When** a second writer appears **Then** it is refused or serialized
**And** readers use `read_only=True`
**And** the test fails if the boundary is removed

### Story 25.3: Validation errors render inline

As an operator on an HTMX form,
I want 422 arrays as Django `ValidationError`s,
So that I see field errors in place.

**Type:** feature • **Effort:** S • **Deps:** S-18.1 • **FR/AD:** FR-28 • resilience BS-7
**Given** a rejected submission **When** the response renders **Then** errors appear inline on the originating surface
**And** `PydanticFormErrorBridge` lives in `django-pyforge`
**And** the test fails if the bridge is removed

### Story 25.4: Restarts reconcile

As a mason operator,
I want a killed boot to re-index without duplicating rows,
So that restarts are safe.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** FR-29 • resilience BS-8 • canopy AD-13
**Given** work interrupted mid-flight **When** the process restarts **Then** the effect applies once
**And** reconcile is against PostgreSQL (and RWX files if any), **not** MinIO
**And** the test fails if reconciliation is removed

## Epic 26: Access, secrets, and flags

### Story 26.1: Revoke takes effect on the next request

As a security officer,
I want an IdP role change to apply without a re-login wait,
So that access is actually revocable.

**Type:** feature • **Effort:** M • **Deps:** S-18.2 • **FR/AD:** FR-31 • canopy AD-15
**Given** a user who can open a portal **When** the role is revoked at the IdP **Then** the next request is denied
**And** local group tables are not the authority

### Story 26.2: Manifests carry secret references only

As a platform operator,
I want rendered Helm to contain `secretKeyRef`s and never secret values,
So that a git-diff of the chart cannot leak credentials.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** FR-32 • canopy AD-19 • parent AD-12
**Given** `helm template` (or Kustomize) output **When** a secret check runs **Then** it fails if a secret *value* appears
**And** pods consume env/file mounts; the app does not call a secrets HTTP API
**And** Vault injector / CSI / extra secrets sidecar is out of this chain without a dated Dream entry

### Story 26.3: OpenFeature packages on the channel (operator gate)

As a platform operator,
I want flag libraries from conda-forge,
So that CAP-13 can evaluate offline.

**Type:** chore • **Effort:** — • **Deps:** — • **FR/AD:** FR-33 • canopy AD-16
**Blocked:** operator-owned packaging (`openfeature-sdk`, `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`, `cachebox` 5.x). This story does **not** author recipes.
**Given** those packages on the platform channel **When** the env solves **Then** S-26.4 may start
**And** until then S-26.4 stays blocked

### Story 26.4: One flag flips three surfaces without a redeploy

As a platform operator,
I want to change one JSON flag and see Django, MCP, and CLI obey,
So that behaviour flips in an air gap without a rollout.

**Type:** feature • **Effort:** L • **Deps:** S-26.3 • **FR/AD:** FR-34 • canopy AD-11
**Given** one JSON tree (ConfigMap from `src/platform/config/flags.json`) **When** a flag value changes on disk **Then** all three surfaces observe it with no egress
**And** the in-process FILE provider watches the mount — no Deployment rollout, no Reloader, no flagd sidecar
**And** two trees is a review-blocking finding
**And** CLI uses the same bytes (host fetch or local-dev file)

## Epic 27: Schema change is governed

**HARD:** S-19.1 (FR-9b) before any story here that revokes app-role DDL.

### Story 27.1: Liquibase on the channel (operator gate)

As a platform operator,
I want Liquibase 5.0.4+ inside the platform image,
So that production DDL has an auditable tool.

**Type:** chore • **Effort:** — • **Deps:** — • **FR/AD:** FR-21 • canopy AD-16
**Blocked:** operator-owned packaging (`liquibase` ≥5.0.4, vendored PostgreSQL JDBC, no new image). This story does **not** author recipes.
**Given** the package on the channel the platform env consumes **When** the env solves **Then** S-27.2 may start

### Story 27.2: Pre-upgrade Job and DML-only app role

As an auditor,
I want schema change applied by a migration role before pods start,
So that the application cannot ALTER itself.

**Type:** feature • **Effort:** L • **Deps:** S-27.1, S-19.1 • **FR/AD:** FR-21a, FR-22, FR-24 • canopy AD-9
**Given** a chart upgrade **When** hooks run **Then** Job weight −1 runs `liquibase update` on the platform image, then the shipped Job runs `migrate --fake`
**And** `preserveSchemaCase` is off; schema names lowercase; Job connects directly with `currentSchema`, not through a pooling proxy
**And** schemas are exactly `public`, `langflow_schema`, `dbgpt_schema`, `liquibase`
**And** app role `CREATE`/`ALTER`/`DROP` is refused by PostgreSQL; no init container
**And** changeset ids are `distribution:seq`

### Story 27.3: Stale extraction fails CI

As a developer,
I want a model change without a changeset to break the build,
So that production DDL cannot drift from what was reviewed.

**Type:** feature • **Effort:** M • **Deps:** S-27.2 • **FR/AD:** FR-23 • canopy AD-9
**Given** a model change with no matching Liquibase changeset **When** CI runs `sqlmigrate` extraction **Then** the check fails and names the missing changeset

### Story 27.4: Test databases still migrate

As a developer,
I want `manage.py test` unchanged,
So that governed production DDL does not capture ephemeral DBs.

**Type:** chore • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** FR-25
**Given** the test runner **When** it creates a test database **Then** it still runs Django `migrate`
**And** no test-suite rewrite is required by this epic

## Epic 28: Scribe's graph outlives a file

### Story 28.1: PostgreSQL driver behind the existing port

As a steward operator,
I want the graph store on PostgreSQL/pgvector with a local path remaining,
So that the JSON file is not the production backend.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** FR-35 • parent AD-1, parent AD-5
**Given** the existing `GraphStore` port **When** the suite runs **Then** it passes against both the durable driver and the local path
**And** callers do not branch on which driver is active
**And** concurrent writers do not corrupt the durable store

### Story 28.2: Semantic recall

As an agent,
I want recall that matches meaning, not only tokens,
So that I find nodes lexical overlap misses.

**Type:** feature • **Effort:** M • **Deps:** S-28.1 • **FR/AD:** FR-36
**Given** a target with no lexical overlap **When** semantic recall runs **Then** it returns that target
**And** the lexical path does not

## Epic 29: Every station is five tiers

### Story 29.1: SKF domain skills from station packages

As an autonomous agent,
I want a version-pinned skill compiled from `pyforge-<station>/`,
So that I follow how the station actually works.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** FR-37 • canopy AD-17
**Given** a station that has no skill today **When** SKF compiles from `src/shared/packages/pyforge-<station>/` **Then** an agent loads that skill and follows it on the station's core task
**And** output is agentskills.io-compliant with provenance; `skf-export-skill` is the only write into `CLAUDE.md` / `AGENTS.md`
**And** `conda-forge-expert` is not replaced

### Story 29.2: Personas act only through grammar and MCP

As an operator,
I want each station addressable as a persona,
So that an agent does not freelance against the filesystem.

**Type:** feature • **Effort:** L • **Deps:** S-22.1, S-21.4, S-29.1 • **FR/AD:** FR-38 • canopy AD-14, AD-17
**Given** a station persona **When** it completes a station task **Then** the transcript shows only FR-13 grammar and FR-11 MCP — no direct filesystem and no ad-hoc HTTP
**And** personas are BMAD launcher/agent skills that consult the CAP-15 content skill

### Story 29.3: Five-tier check

As a platform operator,
I want completeness to fail CI when a tier is missing,
So that "done" cannot mean CLI-only.

**Type:** chore • **Effort:** S • **Deps:** S-29.2 • **FR/AD:** FR-39 • canopy AD-14
**Given** all eight stations **When** the check runs **Then** it reports each of CLI, portal, service, skill, persona
**And** declaring a station complete with fewer than five fails the check

## Epic 30: The old console is gone

FR-6 inventory is done. Parity build uses Epic 20 + Epic 21.5. Kedro-Viz is not in scope for deletion.

### Story 30.1: Remaining console surfaces have a home

As a platform operator,
I want every runtime-reproducible console view to exist on Lane 1 or a portal,
So that deletion does not drop a live surface.

**Type:** feature • **Effort:** L • **Deps:** S-20.1, S-21.5 • **FR/AD:** FR-6, FR-7 • console-parity-inventory
**Given** the 23-surface inventory **When** this story completes **Then** each runtime-reproducible and mixed surface has a named Canopy home
**And** detector verdicts are a scheduled job, cached result, visible age
**And** editorial content is CMS (Epic 20)
**And** live run state and timing come from the supervisor (S-21.5)

### Story 30.2: Delete the generator and its inbound refs

As a platform operator,
I want the old build path gone, not unlinked,
So that two consoles cannot become permanent.

**Type:** chore • **Effort:** L • **Deps:** S-30.1 • **FR/AD:** FR-7
**Given** proven parity **When** this story merges **Then** the generator, its four pixi tasks, scheduled workflow trigger, and committed data blob are gone
**And** inbound refs (docs, workflows, specs, presentations, scripts, tests — 100+ including the Charter gate) no longer 404 or point at the retired path
**And** the Kedro-Viz tree and its workflow survive
**And** `spec-factory-console` is marked superseded (Marshal Phase 5 records the same retirement)
**And** downstream parsers of the data blob are migrated first

## Canopy obligations (2026-08-24)

**Owner:** `pyforge-steward` owns the Canopy (`src/platform/` host + residual CAP-1..17 over
shipped python-agent-platform work). The Canopy is not a ninth station.

**Build surface:** Epics 18–30 (appended above) are the steward implementation chain for
`spec-pyforge-unifying-strategy`. Cite **parent AD-n** (`spec-python-agent-platform` spine)
vs **canopy AD-n** (`architecture-pyforge-unifying-strategy-2026-08-24`); bare `AD-n` is
review-blocking.

**Shipped work stands:** Epic 11 (Stories 11.1–11.4) remains **done**. Schema isolation
(`langflow_schema`, `dbgpt_schema`, `search_path`, Pattern A/B) is not reopened. FR-22 / canopy
AD-9 supersedes only the **production DDL mechanism** — Epic 27, not a rollback of Epic 11.

**Sequencing:** S-19.1 (FR-9b) before Epic 27 stories that revoke app-role DDL. S-26.3 and
S-27.1 stay **blocked** on operator-owned packaging (canopy AD-16).

**Phase 5 scope:** This block records steward obligations. Peer stations (atlas, marshal,
warden, doctor, herald, mason, scribe) run their own Phase 5 course-correction proposals;
Marshal additionally retires `spec-factory-console`. Open question `lane1-serves-dw-h3` stays
joint with atlas — not answered in steward stories.

## Epic 31: Non-module suite pieces install by class

**Spec binding.** Decomposes `spec-bmad-suite-install-class-wiring` CAP-1..3 (Spec landed
2026-08-24 from `docs/dreams/bmad-suite-install-class-wiring.md`; companion
`install-class-playbook.md` cites parent `install-matrix.md`). **HARD:** Epic 15 stays
**done** — this is a new epic, not 15.5+. CAP-3 five and the WDS skip are not reopened.
`--module skf` is a Spec non-goal. Wrap, don't absorb (method first-install = Epic 14;
loop = `--runner` only). Template is scaffold-only forever.

### Story 31.1: Class-keyed playbook is the operator path
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-install-class-wiring CAP-1
**Surface:** `steward provision --help` (or equivalent CLI pointer), playbook companion
**Given** the six non-module suite pieces **Then** `steward provision --help` names the
class-keyed playbook, and that playbook lists pixi path, cited native wire, and steward
verb/task for each class — no tribal knowledge, native commands cited from
`install-matrix.md` never invented.

### Story 31.2: wired-or-not is class-correct
**Type:** feature • **Effort:** M • **Deps:** S-15.1 • **FR/AD:** spec-bmad-suite-install-class-wiring CAP-2
**Surface:** pipeline-truth report (parent CAP-1)
**Given** the pipeline-truth `wired-or-not` column **Then** each of the six is judged by
its class predicate (installer tree / runner home / plugin enabled / VS Code extension /
scaffold N/A), not a boolean only `--module` targets can satisfy — and template-into-this-repo
never reports wired.

### Story 31.3: Fresh clone class-path is proven
**Type:** feature • **Effort:** M • **Deps:** S-31.1 • **FR/AD:** spec-bmad-suite-install-class-wiring CAP-3
**Surface:** documented/scripted fresh-clone path (CI or recorded run)
**Given** a fresh clone **Then** method core is installed, loop is provisionable via
`--runner`, skf skills are present via its own installer, labs plugin path is documented,
dashboard install task is runnable, and template is N/A unless scaffolding — zero
improvised npm Installer driving from a chat transcript.

**Epic 31 clears to dispatch on 31.1; 31.2 after 15.1 (already done); 31.3 after 31.1.**
