---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
mode: headless-express
updated: '2026-08-02'
currency_review: "Reviewed 2026-08-02 — the architecture spine's own currency_review confirms its FR-1..FR-18 binds are unchanged. Epic/story breakdown re-checked against that unchanged architecture and confirmed current; no changes made."
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
