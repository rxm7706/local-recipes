---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/console-parity-inventory.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
mode: headless-express
updated: '2026-09-20'   # chain-currency cascade after Stories 61.1–61.3 landed (PRs #1528, #1532, #1539; spine re-stamped 2026-09-20). Prior '2026-09-17'   # chain-currency arch→epics after the 2026-09-17 one-chain fold remint; Fold provenance heading already names CAP-1..145
currency_review: "Reviewed 2026-09-17 (arch→epics cascade after the spec→prd→arch re-stamps for the one-chain steward fold) — validated against the re-dated ARCHITECTURE-SPINE.md (updated 2026-09-17): no AD added or changed. Fold provenance heading already cites spec-pyforge-steward CAP-1..145; historical stories keep sequential epic numbers 1..64. Every Story heading still maps 1:1 to a sprint-status-ledger.yaml key. No blocked ledger keys flipped. Reviewed 2026-09-14 (fleet-picture follow-up audit, undecomposed-Spec sweep) — spec-platform-image-one-pixi-env (status `shipped`, verified 2026-09-11) had zero Epic/Story despite all three CAPs being real, tested, and running (`59083b8391`, 2026-08-25): retroactive Epic 57 added, mirroring the Epic 38/39 precedent — no new implementation, ledger keys 57-1/57-2/57-3 added at `done`, every Story heading still maps 1:1 to a sprint-status-ledger.yaml key. Same sweep corrected spec-intelligence-hub's stale frontmatter (Dream `dreamt`→`realized`, Spec `ready`→`shipped` — Epic 53 was already 5/5 done, decomposition was NOT missing, no epics.md change needed there) and confirmed spec-build-league-scorecard's `draft` status is correctly parked (operator-owned measure set, not overdue). Reviewed 2026-09-08 (arch→epics cascade after the spec→prd→arch re-stamps for spec-pyforge-steward's 2026-09-08 memlog motion) — validated against the re-dated ARCHITECTURE-SPINE.md (updated 2026-09-08): no AD added or changed. One new Story since the last review — Story 43.7 (Sidecar runtime validation on Python 3.14), hand-authored 2026-09-08 into the existing Epic 43 to own the sidecar runtime validation mason/DW-13-2-2 had deferred to Story 43.6, which closed done without doing it. Its ACs were CORRECTED the same day before implementation: the Celery half is not achievable against this sidecar (no celery/redis package in the env, no broker in container-dbgpt, and the Containerfile assigns that wiring to Stories 11.2/11.3), so 43.7 owns the SQLite metadata-store proof and a real API round-trip instead; it decomposes pap:CAP-5/CAP-6 and mints no new capability. Its ledger key 43-7-sidecar-runtime-validation-on-python-3-14 was added at backlog, so every Story heading still maps 1:1 to a sprint-status-ledger.yaml key. Reviewed 2026-09-06 (new chain spec-bmad-suite-lifecycle → PRD → spine → Story 14.9 + Epics 46/47; ledger 14-6/7/8 → done, 45-2 → backlog; see the 2026-09-06 note at end of file). Reviewed 2026-09-05 (arch→epics cascade after the spec→prd→arch re-stamps for spec-pyforge-steward's 2026-09-05 memlog motions + the new spec-bmad-eval-quality) — validated against the re-dated ARCHITECTURE-SPINE.md (updated 2026-09-05): no AD added or changed; one new Epic since the last review — Epic 45 (Story 45.1 in-progress, 45.2 blocked), hand-authored 2026-09-05 to decompose spec-bmad-eval-quality CAP-1/CAP-2; every Story heading still maps 1:1 to a sprint-status-ledger.yaml key (sprint-ledger-sync --repair-feed + story-status-check re-run same day). Reviewed 2026-08-31 (arch→epics cascade, chain-currency sweep — research→brief→PRD→arch cascade folding technical-pyforge-station-dossier-2026-08-30.md in) — validated against the re-dated ARCHITECTURE-SPINE.md (updated 2026-08-31): no AD added or changed (canopy:AD-21 gained a corroborating 'Realization 2026-08-31' note only, confirming core.hooks already live and used by all 7 non-core stations — no new obligation on any Story here), no new CAP; every Story heading still maps 1:1 to a sprint-status-ledger.yaml key, all 170 real story keys done (the 38 epic-retrospective entries are optional flags, not undone work). Prior 2026-08-29 (arch→epics cascade after the arch spine re-dated, spec-surface drift catch-up + retroactive Epic 38) — validated against the re-cut ARCHITECTURE-SPINE.md: no AD changed, Epic 38 (spec-mcp-factory-stdio-translator, retroactive, own owned spec) sits outside the spine's CLI-package boundary same as Epics 9-37; every Story heading still maps 1:1 to a sprint-status-ledger.yaml key (38/38 epics, 132/132 stories done). Prior 2026-08-25 — lane1-serves-dw-h3 answered no (Wagtail /cms/ ≠ LaSuiteClient Docs REST). Prior 2026-08-24 (Canopy Phase 6 readiness) — spec-pyforge-unifying-strategy Epics 18–30 appended; verdict CONCERNS-proceed (packaging gates). See planning-artifacts/implementation-readiness-report-2026-08-24.md. Prior review 2026-08-15 (fleet-wide decomposition audit) — Story 8.7 added (canopy:FR-140, spec-jira-github-projects-sync's CAP-1 residual, previously undecomposed per Story 8.1's own AF-5 audit note); spec-pyforge-steward and spec-bmad-module-provisioning frontmatter status fields corrected (blank/stale-draft -> shipped, both fully decomposed and done). Prior review 2026-08-10 (Phase 1 backlog-truth audit) — 10 false Status lines corrected, Epic-8 audit note + 8.1 delivery note added; see planning-artifacts/implementation-readiness-report-2026-08-10.md. Prior review 2026-08-02."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (marshal:AD-72).
epics_role: canonical
canopy_chain: pyforge-unifying-strategy
canopy_stepsCompleted: [1, 2, 3]
---

# pyforge-steward - Epic Breakdown

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-steward reminted absorbed capabilities as CAP-1..145. Historical stories keep their sequential epic numbers (already 1..N with no gaps). This heading is the INV-A citation window: `spec-pyforge-steward` CAP-1..145.

**2026-09-17 arch→epics validation.** Re-read ARCHITECTURE-SPINE.md after the 2026-09-17
prd→arch cascade. No AD added or changed. Story headings still map 1:1 to
`sprint-status-ledger.yaml` keys. No blocked ledger keys flipped.

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
NFR-6: Enterprise/air-gap routing is inherited unchanged from `docs/explanation/enterprise-deployment.md` — any new outbound endpoint adds one row to the existing `*_BASE_URL` override table, never a parallel config mechanism (AD-9).
NFR-7: Credential values are never printed — `steward keys list`/`audit` output never contains a raw secret value under any flag combination, enforced by a dedicated `tests/meta/` invariant test.

### Additional Requirements (from Architecture)

- **Starter/scaffold** (Structural Seed): `src/shared/packages/pyforge-steward/` as a pixi build workspace member mirroring `pyforge-warden` — `hatchling` build backend, `pixi-build-python` conda-package wrapper, `[project.scripts] steward = "pyforge.steward.cli:main"`, dedicated `[feature.pyforge-steward]` repo-root pixi block + lean `no-default-feature = true` environment. **This lands in Epic 1 Story 1.1** (the PRD's tentative standalone "Epic E — Packaging & Test Scaffold" is deliberately folded in here rather than kept as its own epic — see Epic Design Note below).
- **Shared `Duty` protocol + exit-code sole ownership** (AD-7, AD-8): `interfaces.py` (`Duty` Protocol + `DutyResult`) and `cli.py`'s exit-code-owning dispatcher are established once, in Epic 1 Story 1.1, and reused unchanged by Epics 2-4.
- **Config file locations** (Consistency Conventions): repo-root `.steward/` dotdir, tracked, independent of the active BMAD project — `budget.yaml`, `keys-inventory.yaml`, `*.age` payloads.
- **Test-tier layout**: `tests/unit/`, `tests/meta/` (invariants, e.g. NFR-7), `tests/fixtures/` (data, never collected). **Superseded 2026-09-07** (marshal Story 32.5, `spec-fleet-consistency-standard` CAP-2): established in Story 1.1 as `tests/unit/` + `tests/conformance/` (FR-level behavioural contracts, incl. the FR-7 regression test) + `tests/meta/`, mirroring `pyforge-warden`'s tree. The `conformance/` tier folded into `tests/unit/` — its 32 files are CLI-verb contract tests this station's own `test-architecture.md` already classified as unit level, and the fleet coverage gate's suite map recognised no tier by that name, so not one of them was ever measured. `pyforge-warden`, cited above as the model, folded its own `conformance/` into `tests/integration/` in the same pass — those 19 are oracle and engine gates, integration weight. Same name, two different concepts, which is why the fold is by level rather than by name.
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
**And** `pixi run -e pyforge-steward pyforge-steward-test` runs a passing (if minimal) `pytest` suite under `tests/unit/`, `tests/conformance/`, `tests/meta/` *(the `tests/conformance/` tier folded into `tests/unit/` on 2026-09-07, Story 32.5 — the assertion is unchanged, its file moved.)*

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
**Then** `tests/conformance/` contains a named test asserting the resolver's host-gating behavior fails loudly (test failure) if the gating logic is ever removed or bypassed — this is FR-7's regression test, landing here because it is a direct property of the resolver this story builds, not a separate later concern *(the `tests/conformance/` tier folded into `tests/unit/` on 2026-09-07, Story 32.5 — the assertion is unchanged, its file moved.)*

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

**Given** a change to `pyforge.doctor.sources.fleet_scan`'s output between runs
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

**Value delivered.** The two stations stop overlapping. Marshal's marshal:AD-71 named both of
these as "actioned in Steward's chain" when the build-line/estate seam was ratified;
until this epic they existed only as a claim in another station's architecture, which is
exactly the unowned-obligation shape the seam was meant to end.

### Story 5.1: Retire `provision --runner bmad-loop` in favour of `marshal init`

As the operator,
I want one command that provisions a loop home,
So that two stations do not ship two ways to make the same thing, one of them wrapping
a legacy script.

**Type:** change • **Effort:** S • **Deps:** — • **FR/AD:** AD-5 (this station), Marshal marshal:AD-71
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

**Type:** feature • **Effort:** XS • **Deps:** — • **FR/AD:** Marshal canopy:FR-136..canopy:FR-139, marshal:AD-71
**Surface:** `deploy.py`, `tests/`

**Why.** marshal:AD-71 makes the ledger a two-sided contract: Marshal produces it and is
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
**jira:AD-10** was added for the baseline's storage contract and lifecycle. 8.1's frozen
intent-contract was re-issued from that amendment on 2026-08-10. **Never reintroduce a timestamp
comparison on the correctness path** — `updated_at` may only select candidates under
`trigger=schedule`, never decide.

**Audit note (Phase 1 backlog-truth, 2026-08-10 —
`planning-artifacts/implementation-readiness-report-2026-08-10.md`).** 8.1 landed (PR #397);
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
fake-transport-tested. Assignee and identity-link propagation shipped as Story 8.7
(closes audit AF-5). The live-pair demonstration remains an open coverage-debt row.*

### Story 8.2: Zero-loop guarantee
**FR/AD:** FR-28 (spec-jira-github-projects-sync CAP-2) • **Effort:** M • **Deps:** S-8.1
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
**FR/AD:** FR-29 (spec-jira-github-projects-sync CAP-3) • **Effort:** S • **Deps:** S-8.1
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
**FR/AD:** FR-30 (spec-jira-github-projects-sync CAP-4) • **Effort:** XS • **Deps:** S-8.1, S-8.4
**Given** a batch containing one unlinked item **Then** every other item completes and the
unlinked one emits a named, greppable error.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.6: Explicit status-vocabulary translation
**FR/AD:** FR-31 (spec-jira-github-projects-sync CAP-5) • **Effort:** S • **Deps:** S-8.1
**Given** any status crossing the boundary **Then** it passes through a reviewable mapping;
an unmapped value is a hard logged failure, never a pass-through inventing a state.
**Status:** done — *corrected 2026-08-15 (fleet-wide decomposition audit): sprint-status-ledger.yaml
already carried this as `done`; this inline line was simply never updated.*

### Story 8.7: Assignee and identity-link propagation
**FR/AD:** canopy:FR-140 (spec-jira-github-projects-sync, CAP-1 residual; found undecomposed,
2026-08-15 fleet-wide decomposition audit) • **Effort:** M • **Deps:** S-8.1
**Given** a status/assignee/link change on either board **Then** the assignee and identity
link propagate to the other side too, no human action on the receiving side — the two-thirds
of CAP-1 Story 8.1's own frozen intent-contract deliberately narrowed away (status-field-only,
fake-transport-tested) and its own audit note (AF-5) named as undelivered with no owning
story until this one. Uses the same reconcile/baseline machinery Story 8.1 already
established (AD-5's value-comparison guard, jira:AD-10's baseline contract) — never a second
propagation path.
**Status:** done — *code on main via PR #544 (`b0072f42d3`); ledger key
`8-7-assignee-and-identity-link-propagation` already `done` (PR #548). This inline
line was the leftover that invited a duplicate story (DW-FU-8-7-7).*

## Epic 9: Secure live dashboards

**Value delivered.** The reusable role-based live-dashboard pattern of
`spec-secure-live-dashboards` (ready, 8 CAPs, architecture final 2026-08-09): identity at the
ASGI boundary, declared row-isolation, role-built navigation, a see-what-was-seen audit
trail, server-gated export, a shipped perimeter, non-vacuous proof tests, and hosted-or-static
without a fork. Atlas's Vizro board is the first adopter, not the subject. ASGI stack ships as
the `pyforge-steward[dashboard]` **optional extra** per uc:AD-1 — never a base
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
deployment refused without it), **sld:AD-11/sld:AD-12** (per-message isolation), **sld:AD-14** (SQLite
dev / Postgres deploy). Each is cited by the story that owns it — an earlier draft cited
only AD-1 and was refused on review.

### Story 9.1: Identity at the boundary, declared isolation, and the cache invariant
**Type:** foundation • **Effort:** L • **Deps:** none • **FR/AD:** sld:CAP-1, sld:CAP-2; AD-4, AD-5, sld:AD-14
**Surface:** ASGI middleware, adopter-declaration schema, cache layer
**Given** a request **Then** identity and role arrive from the request at the ASGI boundary
(the pattern authenticates no one) and the adopter DECLARES its access column and roles
rather than implementing filtering. **AD-4:** identity headers arriving from outside the
declared ingress refuse the start, not the request. **sld:CAP-2's real invariant (AD-5):** two
concurrent users of different roles produce **one** upstream fetch and **a role-filtered
frame is never written back to the shared cache** — asserted by test, not documented.
**sld:AD-14:** SQLite in dev, Postgres in deployment.

### Story 9.2: An unauthorized page is absent, not hidden
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** sld:CAP-3; AD-6
**Surface:** navigation builder, API surface
**Given** a caller's role **Then** the navigation tree is constructed from it — a page the
user cannot access does not exist in their tree — and the API shape enforces
filter-then-search (AD-6), never search-then-filter.

### Story 9.3: The audit trail records what was seen
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** sld:CAP-4; AD-7, sld:AD-11, sld:AD-12
**Surface:** audit-trail store, retention config
**Given** any data load, filter, navigation or export **Then** a durable role-isolated trail
entry records what was actually seen, not merely that an event fired; **retention is declared
with no default and deployment is refused without it** (AD-7); per-message isolation holds
(sld:AD-11/12).

### Story 9.4: Export gated server-side
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** sld:CAP-5
**Surface:** export endpoint
**Given** an export request **Then** authorization is enforced server-side (no client-side
gate is trusted) and the export may be encrypted.

### Story 9.5: The perimeter ships with the pattern
**Type:** infra • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** sld:CAP-6; AD-1
**Surface:** `pyforge-steward[dashboard]` extra, deployment manifests, edge config
**Given** an adopter **Then** they receive a production-shaped runtime rather than assembling
one: Django+Channels+Daphne via the optional extra **plus the edge that terminates TLS and
enforces network policy** (sld:CAP-6's clause an earlier draft dropped).

### Story 9.6: Isolation proven by tests that cannot pass vacuously
**Type:** test • **Effort:** L • **Deps:** S-9.2, S-9.3, S-9.4, S-9.5 • **FR/AD:** sld:CAP-7
**Surface:** proof suite
**Given** the proof suite **Then** it impersonates distinct identities and **fails loudly if
isolation is removed** — a suite that cannot fail is a failing suite; the cache invariant
(9.1) and the retention refusal (9.3) each carry a mutation-proof case.

### Story 9.7: Hosted or static, no fork
**Type:** feature • **Effort:** M • **Deps:** S-9.1 • **FR/AD:** sld:CAP-8
**Surface:** static-export path
**Given** a board needing no isolation **Then** the same definition publishes as a static
GitHub-Pages site — mutually exclusive with role isolation, never a second codebase.

## Epic 10: python-agent-platform — the host takes root

**Spec binding.** Decomposes `spec-pyforge-unifying-strategy` host platform (`pap:CAP-1..145`;
merged from `spec-python-agent-platform` by Story 48.8). All open questions resolved
2026-08-14, operator: OCP-first with GKE as a CI portability profile; in-repo at
`src/platform/` per the monorepo goal; ship on py3.12 with py3.14 as a release gate; Docker
AND Podman with rootless Podman as the reference posture. Stories cite `pap:CAP-*` /
`pap:AD-*` directly — the Unifying Spec is the contract; no new FR numbers are minted.
Story 10.4 is conda-forge
feedstock work and per the repo's Rule 1 its dev session MUST invoke the
`conda-forge-expert` skill; it is the py3.14 unblocker and rides in parallel (no deps).

### Story 10.1: The host renders into src/platform
**Type:** foundation • **Effort:** L • **Deps:** none • **FR/AD:** pap:CAP-1
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
**Type:** infra • **Effort:** M • **Deps:** none • **FR/AD:** pap:CAP-5
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
**Type:** infra • **Effort:** L • **Deps:** S-10.1, S-10.2 • **FR/AD:** pap:CAP-6
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
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** pap:CAP-5 (release gate)
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
**Type:** infra • **Effort:** M • **Deps:** S-10.3 • **FR/AD:** pap:CAP-6, pap:AD-17
**Surface:** `src/platform/compose/dbgpt/`, platform CI
**Given** DB-GPT's Pattern-B deviation (pap:AD-14, dated 2026-08-21 in `db-gpt-django-plugin.md`)
**Then** a `docker-compose.yml` service builds and runs DB-GPT as its own container (model
worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as
Story 10.3's image, wired into the local-dev tiers (pap:AD-16) and platform CI so 11.2's sidecar
integration is testable end-to-end without a manual DB-GPT setup step. Added 2026-08-21 —
Story 10.3 shipped "one image, both engines" before this deviation existed; this is the
additive counterpart for the engine that no longer fits that image, not a correction to 10.3.

## Epic 11: The engines join as pluggable apps

**Spec binding.** `pap:CAP-2`, `pap:CAP-3`, `pap:CAP-4` and the isolation/statelessness
constraints of `spec-pyforge-unifying-strategy` § Host platform. Pattern A per the plugin
dreams ([[langflow-django-plugin]],
[[db-gpt-django-plugin]]) is the default; a sidecar fallback requires a dated deviation in
the Dream first (pap:AD-14) and is selected through pap:AD-17's per-engine config switch, added
2026-08-21 after DB-GPT's Pattern-B deviation — see the 2026-08-21 sprint-change-proposal.
Langflow (11.1) is unaffected and stays on Pattern A.

### Story 11.1: Langflow joins as a pluggable app
**Type:** feature • **Effort:** L • **Deps:** S-10.1, S-10.2 • **FR/AD:** pap:CAP-2
**Surface:** `src/platform/langflow_integration/`
**Given** the `langflow_integration` app **Then** an ASGI dispatcher mounts Langflow's app at
`/api/v1/`, `/health`, `/langflow/`; a `RunSQL` migration provisions `langflow_schema`;
`LANGFLOW_DATABASE_URL` carries the `search_path` suffix; no local-disk state path survives;
and a flow executes end-to-end through the mount with its tables provably confined to
`langflow_schema`.
**And** (added 2026-08-14, pap:AD-16 — folded here rather than into 10.2, whose contract was
frozen mid-dev under the graceful stop) a `platform-dev` pixi feature exists providing
per-user `postgresql` + `pgvector` + `redis-server` (plus `kubernetes-helm`/
`kubernetes-client`) so this story's schema work — and all of Epic 11 — runs on the
guaranteed baseline with no managed services and no containers; its pixi.toml edit carries
the standard env-count reconcile ripple.

### Story 11.2: DB-GPT joins via its configured integration pattern
**Type:** feature • **Effort:** L • **Deps:** S-10.1, S-10.2, S-10.5 • **FR/AD:** pap:CAP-3, AD-6 (bounded exception, 2026-08-21), pap:AD-17
**Surface:** `src/platform/dbgpt_integration/`
**Given** the `dbgpt_integration` app configured for Pattern B (pap:AD-17 — `dbgpt: B` in the
pattern registry, per the 2026-08-21 deviation dated in `db-gpt-django-plugin.md`) **Then** a
Django data migration provisions `dbgpt_schema` exactly as Pattern A would (Django ORM never
crosses in; DB-GPT's Alembic never touches `public`); the sidecar built by Story 10.5
(`docker-compose`-managed, its own FastAPI/AWEL process) is registered in the pap:AD-17 pattern
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
**Type:** feature • **Effort:** M • **Deps:** S-11.1, S-11.2 • **FR/AD:** pap:CAP-4, pap:AD-17
**Surface:** `src/platform/config/celery*`, worker wiring
**Given** Celery over Redis **Then** LLM/AWEL work dispatches to workers that call each
engine per its pap:AD-17 pattern — Pattern-A engines in-process, Pattern-B engines (DB-GPT) via a
REST call to the sidecar's AWEL endpoint (never through the public edge) — the host stays
responsive under a long-running agent task, and the new failure mode (timeout / partial
result, now including a sidecar-unreachable case) is named and handled, not discovered.

### Story 11.4: Isolation and statelessness proven
**Type:** test • **Effort:** L • **Deps:** S-11.1, S-11.2 • **FR/AD:** pap:CAP-2, pap:CAP-3 (success clauses), pap:AD-17
**Surface:** `src/platform/tests/`
**Given** the proof suite **Then** schema inspection asserts each engine's tables live only
in its schema; a container-replacement simulation covers BOTH the in-process Pattern-A case
(kill + fresh start loses no flow, no session, no state) AND the Pattern-B sidecar case (kill
+ restart the `docker-compose` service, proven against the same shared `dbgpt_schema`); and
the suite fails loudly if isolation or statelessness is removed, under either pattern — a
suite that cannot fail is a failing suite (the 9.6 discipline).

## Epic 12: Deploy anywhere, including nowhere-connected

**Spec binding.** `pap:CAP-6` from `spec-pyforge-unifying-strategy` § Host platform and the Q1
resolution (OCP first, GKE as a CI portability profile over a vanilla-Kubernetes core chart).

### Story 12.1: The vanilla chart with an OCP overlay
**Type:** infra • **Effort:** L • **Deps:** S-10.3 • **FR/AD:** pap:CAP-1, pap:CAP-6
**Surface:** `src/platform/deploy/`
**Given** a Helm chart of plain Deployment/Service/Ingress (or Gateway API) resources plus a
thin OCP Route overlay **Then** the platform deploys onto a namespace carrying only
PostgreSQL, Redis and the platform image; the image passes `restricted-v2` (arbitrary UID,
no root); and nothing in the core chart is OCP-specific.

### Story 12.2: GKE as a portability profile
**Type:** infra • **Effort:** S • **Deps:** S-12.1 • **FR/AD:** pap:CAP-6 (portability clause)
**Surface:** platform CI
**Given** the same chart **Then** a CI smoke profile deploys it against a GKE-shaped target
(kind or equivalent) with the Ingress path — a profile, never a second implementation.

### Story 12.3: Air-gap parity is a failing check
**Type:** test • **Effort:** L • **Deps:** S-10.3, S-12.1 • **FR/AD:** pap:CAP-6
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

**Spec binding.** Decomposes `spec-multi-repo-workspaces` CAP-1..145 (seeded from the
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

### Story 14.6: The installer is driven on purpose, and a no-op apply is a refusal
**Type:** feature • **Effort:** M • **Deps:** 14.2 • **FR/AD:** spec-bmad-method-core-upgrade CAP-6
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` (apply path), release catalogs
**Given** a clean tree and a target release **When** `steward upgrade bmad-core --apply`
runs **Then** the installer is invoked with `--directory <repo>`, `--modules <every module
`_bmad/_config/manifest.yaml` lists>` (core, bmm and each `source: custom` module) and a
closed stdin, with `node` / `bmad-method` resolved from the repo's pixi env when they are
not on PATH — no wrapper script — **And** an installer exit 0 that left zero changed paths
is reported `ok=False` with failure-modes.md trap 12 named (the 2026-09-06 first apply was
exactly that silent no-op), never a green.

### Story 14.7: Custom modules survive the core apply
**Type:** feature • **Effort:** M • **Deps:** 14.6 • **FR/AD:** spec-bmad-method-core-upgrade CAP-7
**Surface:** `upgrade.py` (apply + reconcile), release-catalog schema (`custom_modules:`), steward CLI
**Given** the installed manifest lists a `source: custom` module (skf) and the release
catalog names its own installer, config files and optional pin **When** the apply runs
**Then** the module is selected for the core apply, its config files are snapshotted before
and restored after, its own installer (`bmad-module-skill-forge update`) runs after the core
apply from the repo root, and the report names each restored file — **And** the fixture
replaying 2026-09-06 (skf deselected and deleted by `-y`; `skf-campaign` undeclared in
`marketplace.json`; `_bmad/skf/config.yaml` regenerated with a literal
`{project-root}/{value}`) ends with the module's skill dirs equal to its packaged source and
its config equal to the pre-apply bytes plus the installer's own appended keys
(failure-modes.md traps 13–14).

### Story 14.8: Local edits to installer-owned files are found before and re-applied after
**Type:** feature • **Effort:** L • **Deps:** 14.6 • **FR/AD:** spec-bmad-method-core-upgrade CAP-8
**Surface:** `upgrade.py` (pre-flight + reconcile), steward CLI (`--installed-package-root`)
**Given** the cached package of the installed version (`~/.cache/rattler/cache/pkgs/bmad-method-<v>-*/lib/node_modules/bmad-method/src`, or `--installed-package-root`) **When** the
pre-flight runs **Then** every installer-owned file (`.claude/skills/<manifest skill>/**`,
`_bmad/scripts/*`) that differs from its packaged copy is listed as a local customization in
the CAP-1 report **And** after the apply each one is re-applied by three-way merge (ours =
pre-apply bytes, base = old upstream, theirs = new upstream): clean merges written,
conflicts flagged with the hunk saved beside the report, never resolved by taking upstream;
`resolve_config.py` gets the old→new upstream delta replayed on the restored copy instead of
a bare `.bak` restore — **And** the fixture replaying 2026-09-06's seven files ends with six
clean merges and one flagged conflict (step-01 `done` routing) (failure-modes.md trap 16).

### Story 14.9: The apply retires deprecation shims on purpose (`--no-shims`)
**Type:** feature • **Effort:** S • **Deps:** S-14.6 • **FR/AD:** spec-bmad-method-core-upgrade CAP-9 • spec-bmad-suite-lifecycle CAP-10 • lifecycle spine AD-5, AD-7
**Surface:** `upgrade.py` (apply argv + pre-flight report), steward CLI (`--no-shims`), `tests/unit/test_upgrade_apply.py`, `tests/unit/test_upgrade_preflight.py`
**Corrected 2026-09-06** (found during marshal Story 30.5; operator-directed spec correction, same session): the original **And** clause below naming a refusal keyed on "the marshal harness template or any rendered loop-home policy still emits the retired `bmad-dev-auto`" was FALSE — verified directly against the installed `bmad_loop` 0.11.1 package source. `DevPolicy.skill` is a PERMANENT internal adapter discriminator (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated) that must read `"bmad-dev-auto"` forever, on every era; the skill actually invoked is resolved separately from disk at runtime, independent of this field. Every loop-home's `policy.toml` (and the harness template that renders it) will emit this literal forever by design — a refusal keyed on finding it would refuse `--no-shims` permanently, with no way to ever satisfy it. That refusal clause, its `_shim_retirement_blockers`/`refuse_shim_retirement_not_ready` implementation, and the `--loops-home` flag that only existed to parameterize it are REMOVED. The "prove-landed validates... whose policy already names `bmad-build-auto`" clause below is also corrected: no loop-home policy ever names `bmad-build-auto` — that field stays `bmad-dev-auto` forever. The `Deps` field's "after marshal 30.5" cross-station note is removed — no harness change precedes this story any more (era-alignment CAP-12 corrected to match).
**Given** an installed core whose manifest reads `installShims: true` **When** `steward upgrade bmad-core --target <installed-or-newer> --apply --no-shims --branch <name>` runs **Then** the installer argv carries `--no-shims` after `--modules …`, the pre-flight report lists every shim the manifest names as "to retire" (21 at 6.12.0: the 20 `v6-shims` plus `bmad-generate-project-context`), and a same-version run is accepted as a retirement run — the removed dirs are a real diff, not a trap-12 zero-diff refusal
**And** after the run `_bmad/_config/manifest.yaml` reads `installShims: false`, the shim rows are gone from `skill-manifest.csv`, CAP-7 restored skf's config and ran its own installer (`--pin skf=v2.1.0`, pinned by Story 46.7), CAP-8 re-applied every listed local customization by three-way merge with no `.customization-conflict` sibling left, and `prove-landed` validates 8/8 loop homes
**And** the flag is refused with a named reason when any `_bmad/custom/<legacy-name>.toml` exists (trap 2) — the sole pre-apply `--no-shims` refusal, unconditional and pre-existing, unaffected by the correction above
**And** the argv assertion and the 21-row report each have a unit test with an injected runner; the live run is Session 2's step 9 (`open-items-register.md`)
**Status:** done
**Outcome (2026-09-06):** implementation + CAP-9 false-positive correction landed same session.
The live run (Session 2 step 9) executed the same day: `installShims: true -> false`, 21 shim
dirs deleted, CAP-7 skf reinstall ok, CAP-8 three-way-merged all 8 previously-flagged files
cleanly (no `.customization-conflict`), `_bmad/custom/**` byte-identical, `prove-landed`
verdict PASS 8/8. `pyforge-steward-test`: 1104 passed.

### Story 14.10: The `@next` rehearsal exercises CAP-6's fallback and CAP-8's conflict path, report-only
**Type:** chore • **Effort:** S • **Deps:** S-14.9 • **FR/AD:** spec-bmad-method-core-upgrade CAP-6, CAP-8 (+ answered Q2) • spec-bmad-suite-lifecycle CAP-8 • lifecycle spine AD-7
**Surface:** a throwaway worktree (never merged), the core-upgrade memlog (findings), `release-cadence.md` § The `@next` rehearsal (the recipe, verified verbatim by 46.10)
**Given** npm's `next` dist-tag (`6.12.1-next.0` on 2026-09-06) **When** the rehearsal runs in a throwaway worktree with `--installer` pointed at `npx bmad-method@next`, `--package-root` at the unpacked next tarball, `--installed-package-root` at the cached 6.12.0, one planted conflicting local edit in an installer-owned skill file, and `PATH` without `node` **Then** the report shows CAP-6's pixi-bin fallback resolving `node`, CAP-8 flagging exactly one conflict with its `.customization-conflict` sibling, and CAP-7 restoring skf; findings are appended to the core-upgrade memlog and the worktree is deleted
**And** the rehearsal never counts as the live proof that flips the Spec to `shipped` (a real future release through CAP-6..8 does)


## Epic 15: The bmad-suite channel is a governed product

**Spec binding.** Decomposes `spec-bmad-suite-channel-product` CAP-1..145 (Spec landed
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

**Spec binding.** Decomposes `spec-local-ocp-hybrid-environment` CAP-1..145 (Spec landed
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

**Spec binding (2026-08-24).** Story 12.9 decomposes `spec-ocp-as-a-portability-profile` CAP-1..145
(chain Spec landed 2026-08-24 from `docs/dreams/ocp-as-a-portability-profile.md`; INV-1 requires
the folder `spec-ocp-as-a-portability-profile/`, not a `spec-12-9-*` story-spec name). Parent
`spec-python-agent-platform` CAP-6 / pap:AD-11 remain. Adopted companions: `cluster-bringup-facts.md`,
`spec-12-2-gke-as-a-portability-profile.md`. Runner class is an open question at story time.
Ledger previously marked 12.9 done with no `ocp-portability-smoke` job — flipped to backlog.

### Story 12.9: OCP as a portability profile
**Type:** infra • **Effort:** M • **Deps:** S-12.1, S-12.2 (pattern) • **FR/AD:** spec-ocp-as-a-portability-profile CAP-1, CAP-2, CAP-3 (parent CAP-6 / pap:AD-11)
**Surface:** platform CI (`.github/workflows/platform-ci.yml`), `deploy/README.md` honesty line
**Given** the Story 12.1 OCP overlay and a real OpenShift API (CRC / OpenShift Local — not `kind`)
**Then** an optional Platform CI job (`ocp-portability-smoke`, default off) pushes the shared
platform image via the internal-registry pattern, installs core + overlay, and curls through an
admitted Route — proving SCC-assigned UIDs and the OCP edge path end-to-end; consumes
`cluster-bringup-facts.md` registry commands, does not replace Story 12.7 attended closeout.

## Epic 16: The platform host earns its 15 factors

**Spec binding.** Decomposes `spec-platform-fifteen-factors` CAP-1..145 (seeded 2026-08-22
from the seven-repo external analysis; MIT reference implementations
django-15-factor-base + devinfra — borrow with notices; intake report carries the
inventory). **HARD:** AD-4/pap:AD-17 topology and the 12.1 chart contract untouched — factors
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

# Chain: `spec-pyforge-unifying-strategy` (Epics 18–30)

Headless/express 2026-08-24. Steward ledger already occupies Epics 1–17; this chain **appends**. Cite **parent AD-n** (python-agent-platform) vs **canopy AD-n** (unifying-strategy spine). Packaging FRs are **blocked on the operator** (canopy:AD-16) — not sized as recipe stories. Phase 5 (`bmad-correct-course` × 8, Marshal retires `spec-factory-console`) is **not** an epic. Open question `lane1-serves-dw-h3` stayed out of stories and was **answered no** 2026-08-25.

## Requirements Inventory (Canopy)

### Functional Requirements

canopy:FR-1: Chrome is installable and singular — one `django-pyforge` package; portals do not ship chrome copies. **CAP-1.**
canopy:FR-2: A portal registers itself without host URLconf/settings edits beyond what the portal supplies. **CAP-1, CAP-3.**
canopy:FR-3: App switcher shows only stations the signed-in user may reach; enforcement stays on the station. **CAP-1, CAP-12.**
canopy:FR-4: CMS page edits are live with no deploy or pod restart. **CAP-2.**
canopy:FR-5: Wagtail admin is IdP-only; no local password form; unmapped groups are refused with a clear error. **CAP-2, CAP-12.**
canopy:FR-6: Console parity inventoried before removal. **CAP-2. Satisfied 2026-08-24** (`console-parity-inventory.md`).
canopy:FR-7: Old console build path is deleted (generator, pixi tasks, workflow, data blob, inbound refs); Kedro-Viz survives; `spec-factory-console` superseded. **CAP-2.**
canopy:FR-8: Lane 1 media/renditions work across replicas; no pod-local Lane 1 state. **CAP-2.**
canopy:FR-9: All eight portals resolve same-origin, one session, under `/stations/<name>/`. **CAP-3.**
canopy:FR-9a: `/compliance/` permanent redirect to `/stations/warden/` preserving path and query. **CAP-3.**
canopy:FR-9b: Reusable-app triple; warden becomes `django-warden` / `django_warden_fabric` / `warden_fabric` before CAP-9. **CAP-3.**
canopy:FR-10: Portals render and dispatch; no station internals; no raw HTTP to services. **CAP-3, CAP-6.**
canopy:FR-11: Eight current-spec MCP faces on host ASGI; dual-era `2025-03-26`–`2026-07-28`; echo client revision; no UA branch. **CAP-4.**
canopy:FR-12: Long work is `start`/`get` over PostgreSQL; any replica serves `get`; opaque TTL handles. **CAP-4.**
canopy:FR-13: `pyforge <station> <noun> <verb>` parity with station binaries; CI fails on drift. **CAP-5.**
canopy:FR-14: Services verify audience-bound signed assertions. **CAP-6.**
canopy:FR-15: No trusted-header identity path. **CAP-6.**
canopy:FR-16: Two roles, same board URL, different rows via existing secure-dashboard pattern. **CAP-7.**
canopy:FR-17: Events durable; consumer restart does not drop or double-apply. **CAP-8.**
canopy:FR-18: Poisoned events go to DLQ, do not block the group. **CAP-8, CAP-10.**
canopy:FR-19: Cyclic publish halts at declared depth. **CAP-8.**
canopy:FR-20: Payload validation in domain adapters, not at the stream boundary. **CAP-8.**
canopy:FR-21: Liquibase ≥5.0.4 with vendored PostgreSQL JDBC on the platform channel. **CAP-9. Operator packaging.**
canopy:FR-21a: `preserveSchemaCase` off; Job connects directly with schema on the connection. **CAP-9.**
canopy:FR-22: App role cannot DDL; migration role can. **CAP-9.**
canopy:FR-23: Model change without a changeset fails CI. **CAP-9.**
canopy:FR-24: Helm Job weight −1 then `migrate --fake`; no init container. **CAP-9.**
canopy:FR-25: Test databases still use Django `migrate`. **CAP-9.**
canopy:FR-26: Circuit breaker degrades the caller; async path trips. **CAP-10.**
canopy:FR-27: Single writer for atlas DuckDB. **CAP-10.**
canopy:FR-28: Validation errors render inline. **CAP-10.**
canopy:FR-29: Restart reconciles, does not duplicate. **CAP-10, CAP-8.**
canopy:FR-30: Cache eviction loses no queued task; web and workers scale independently. **CAP-11.**
canopy:FR-31: IdP role revoke takes effect on the next request. **CAP-12.**
canopy:FR-32: No secret *value* in rendered pod specs. **CAP-12.**
canopy:FR-33: OpenFeature + cachebox 5.x on the channel. **CAP-13. Operator packaging.**
canopy:FR-34: One flag flips Django, MCP, and CLI with no egress and no redeploy. **CAP-13.**
canopy:FR-35: Scribe graph operations pass on durable PG and local drivers. **CAP-14.**
canopy:FR-36: Semantic recall returns a result lexical overlap misses. **CAP-14.**
canopy:FR-37: Each **03** station has a SKF domain skill; proven on a station that has none today. **CAP-15.**
canopy:FR-38: Each **03** station persona acts only through canopy:FR-13 and canopy:FR-11. **CAP-16.**
canopy:FR-39: Five-tier completeness of an **03** station is a failing check. 01/02 work is out of denominator. **CAP-15, CAP-16.**
canopy:FR-40: Front door queries run state from a supervisor, never an operator home directory. **CAP-17.**
canopy:FR-41: Completed-run timing is ingested at completion into durable storage. **CAP-17.**
canopy:FR-42: Unreachable supervisor is explicit unavailable plus age, within canopy:FR-26 budget. **CAP-17, CAP-10.**
canopy:FR-43: Shared hook-spec + plugin registration in `pyforge-core`. **CAP-18.**
canopy:FR-44: Warden owns PR-gate hook specs; scanners optional plugins; missing named scanner ≠ fail. **CAP-18.**
canopy:FR-45: Each 03 station extracts one process hook spec; today's backend is the default plugin. **CAP-18.**

### NonFunctional Requirements

NFR-C1: Air-gap — Python/pixi from conda-forge; egress-blocked build is a gate.
NFR-C2: Backing services are PostgreSQL + Redis + Kubernetes only (parent AD-1). Lane 1 media is RWX, not MinIO.
NFR-C3: Stateless pods; replicas are capacity (parent AD-6).
NFR-C4: Django `>=5.2.15,<6`, Python `3.12.*`. Pin move to 5.2.17 is operator maintenance, not chain scope.
NFR-C5: `src/platform/` never imports `pyforge.*` (parent AD-2).
NFR-C6: Long-lived responses keep alive well under 30s; route annotation is not the mechanism.
NFR-C7: Search is PostgreSQL FTS; Wagtail work is Celery, not django-tasks DB/RQ / `django-tasks-celery`.

### Additional Requirements (Architecture)

- Modular monolith: one ASGI process; MCP is a URL pattern, not a roster (canopy:AD-1, canopy:AD-5, canopy:AD-10).
- Citation: `parent AD-n` vs `canopy AD-n`; bare `AD-n` is review-blocking.
- JWT: RS256; claims `sub`/`roles`/`aud=mcp:<station>`/`exp`≤5m/`delegated_by=pyforge-host` (canopy:AD-7). HMAC rejected.
- Events: `pyforge.events` + `pyforge.events.dlq`; `pyforgeloopdepth` ceiling 8 (canopy:AD-8).
- Four PostgreSQL schemas only; `run_state`/`mcp_handles` are tables in `public` (canopy:AD-9).
- Flags: in-process FILE watches the ConfigMap; Reloader/flagd sidecar is parent canopy:AD-14 (canopy:AD-11).
- `start_*` is a supervisor publish (canopy:AD-12).
- CAP-7 consumes `pyforge.steward.dashboard` only (canopy:AD-20).
- Portal models are projections; factory package is the writer (canopy:AD-18).
- CAP-15 skills are SKF content skills; CAP-16 are BMAD launcher skills; `conda-forge-expert` stays hand-authored (canopy:AD-17).
- canopy:FR-9b before any CAP-9 story that revokes app-role DDL.
- One hook-spec + plugin registration in `pyforge-core` (canopy:AD-21, CAP-18). Epics 18–30 must not invent a station-local plugin API.

### UX Design Requirements

Not applicable — no `bmad-ux` contract for this chain. Chrome is `django-pyforge`; Lane 1 is Wagtail; boards consume `spec-secure-live-dashboards`.

### FR Coverage Map (Canopy)

canopy:FR-1: Epic 18 — chrome package
canopy:FR-2: Epic 18 — registration protocol
canopy:FR-3: Epic 18 — role-filtered switcher
canopy:FR-4: Epic 20 — CMS publish without deploy
canopy:FR-5: Epic 20 — Wagtail admin via IdP
canopy:FR-6: Epic 30 — inventory already done; cutover precondition
canopy:FR-7: Epic 30 — console removal
canopy:FR-8: Epic 20 — RWX media + redis-cache renditions
canopy:FR-9: Epic 19 — eight portals
canopy:FR-9a: Epic 19 — `/compliance/` redirect
canopy:FR-9b: Epic 19 — reusable-app triple (before Epic 27)
canopy:FR-10: Epic 19 — portals are projections
canopy:FR-11: Epic 21 — MCP faces
canopy:FR-12: Epic 21 — `start`/`get`
canopy:FR-13: Epic 22 — unified CLI
canopy:FR-14: Epic 18 — assertion client
canopy:FR-15: Epic 18 — no trusted headers
canopy:FR-16: Epic 23 — secure-dashboard boards
canopy:FR-17: Epic 24 — durable events
canopy:FR-18: Epic 24 — DLQ
canopy:FR-19: Epic 24 — loop-depth ceiling
canopy:FR-20: Epic 24 — adapter validation
canopy:FR-21: Epic 27 — blocked operator packaging
canopy:FR-21a: Epic 27 — schema targeting
canopy:FR-22: Epic 27 — app role DML-only
canopy:FR-23: Epic 27 — sqlmigrate gate
canopy:FR-24: Epic 27 — Helm Job −1
canopy:FR-25: Epic 27 — test DB carve-out
canopy:FR-26: Epic 25 — circuit breaker
canopy:FR-27: Epic 25 — DuckDB writer
canopy:FR-28: Epic 25 — inline validation
canopy:FR-29: Epic 25 — restart reconcile
canopy:FR-30: Epic 20 — redis-cache ≠ redis-broker
canopy:FR-31: Epic 26 — IdP revoke on next request
canopy:FR-32: Epic 26 — secret refs not values
canopy:FR-33: Epic 26 — blocked operator packaging
canopy:FR-34: Epic 26 — FILE flags, no redeploy
canopy:FR-35: Epic 28 — Scribe dual driver
canopy:FR-36: Epic 28 — semantic recall
canopy:FR-37: Epic 29 — SKF skills
canopy:FR-38: Epic 29 — personas
canopy:FR-39: Epic 29 — five-tier check
canopy:FR-40: Epic 21 — supervisor query
canopy:FR-41: Epic 21 — timing ingest
canopy:FR-42: Epic 21 — supervisor degrade
canopy:FR-43: Epic 32 — shared hook-spec contract (`pyforge-core`)
canopy:FR-44: Warden Epic 9 — PR-gate plugins (not a steward story)
canopy:FR-45: Epic 32.2 + peer station process-hook epics
canopy:FR-46: Epic 34 — live read-only attach
canopy:FR-47: Epic 34 — Parquet cache
canopy:FR-48: Epic 34 — vectors on the plane
canopy:FR-49: Epic 34 — agent OLTP shield
canopy:FR-50: Epic 34 — station reimplementation

## Epic List (Canopy)

**2026-08-25 drain:** stories 18.1–32.2 are ledger-`done`. Epic *rollup* keys may still read
`backlog` (pre-existing). Do not re-dispatch. Closeout **2026-08-26:** 12-7 `/ht/` and CAP-9
`platform_app` proven; published `/` **200**. Leftover is isolated `mfa` sqlmigrate (fake)
plus optional 12.9 CI. Peers implement CAP-18 as one process-hook story; they do not copy this list.
**2026-08-26 evergreen:** CAP-19 / Epic 34 is the live **query-plane** residual. Do not re-dispatch 18–32.
**2026-08-26 MCP CAP-4:** Epic 35 is the live **cluster mcp-host** residual on `spec-mcp-era-isolation` (not a unifying CAP). Slice 3 stays parked.

### Epic 18: Chrome and the trusted client
An operator sees one estate chrome, and every portal-to-service call carries a verifiable user.
**FRs covered:** canopy:FR-1, canopy:FR-2, canopy:FR-3, canopy:FR-14, canopy:FR-15

### Epic 19: Eight portals, one prefix
All eight stations are same-origin under `/stations/<name>/`; warden's old URL still works.
**FRs covered:** canopy:FR-9, canopy:FR-9a, canopy:FR-9b, canopy:FR-10

### Epic 20: The published front door
Editors publish at `/` without a deploy; media survives replicas; cache eviction cannot drop tasks; admin is IdP-only.
**FRs covered:** canopy:FR-4, canopy:FR-5, canopy:FR-8, canopy:FR-30

### Epic 21: Agents survive; run state is a service
Agents reconnect to in-flight work; the front door queries runs from PostgreSQL, never a laptop disk.
**FRs covered:** canopy:FR-11, canopy:FR-12, canopy:FR-40, canopy:FR-41, canopy:FR-42

### Epic 22: One command grammar
`pyforge <station> <noun> <verb>` reaches every station verb the native binary does.
**FRs covered:** canopy:FR-13

### Epic 23: Boards show only your rows
Two roles hit the same board URL and receive different rows through the estate pattern.
**FRs covered:** canopy:FR-16

### Epic 24: Stations tell each other things
Stations publish CloudEvents that survive poison and cycles, on redis-broker.
**FRs covered:** canopy:FR-17, canopy:FR-18, canopy:FR-19, canopy:FR-20

### Epic 25: Failure stays contained
A dead dependency degrades; DuckDB has one writer; validation is inline; restarts do not double-apply.
**FRs covered:** canopy:FR-26, canopy:FR-27, canopy:FR-28, canopy:FR-29

### Epic 26: Access, secrets, and flags
Revoking a role works on the next request; manifests hold refs not values; one flag flips three surfaces.
**FRs covered:** canopy:FR-31, canopy:FR-32, canopy:FR-33 (blocked), canopy:FR-34

### Epic 27: Schema change is governed
Production DDL is Liquibase under a migration role; the app cannot ALTER; tests still `migrate`.
**FRs covered:** canopy:FR-21 (blocked), canopy:FR-21a, canopy:FR-22, canopy:FR-23, canopy:FR-24, canopy:FR-25

### Epic 28: Scribe's graph outlives a file
The graph port runs on PostgreSQL/pgvector and still has a local path; recall is semantic.
**FRs covered:** canopy:FR-35, canopy:FR-36

### Epic 29: Every 03 station is five tiers
CLI, portal, service, SKF skill, and persona exist for each **03** station, and a check fails when any of those is missing. 01/02 work is not in the check.
**FRs covered:** canopy:FR-37, canopy:FR-38, canopy:FR-39

### Epic 30: The old console is gone
After parity (including supervisor-backed run state), the generator and its inbound refs are deleted.
**FRs covered:** canopy:FR-6 (precondition), canopy:FR-7

### Epic 31: Non-module suite pieces install by class
Non-module suite pieces follow a class-keyed playbook; `wired-or-not` is class-correct.
**FRs covered:** spec-bmad-suite-install-class-wiring CAP-1..145 (not Canopy FRs)

### Epic 32: One plugin API for eight stations
`pyforge-core` ships the shared hook-spec + registration shape; steward deploy-profile adapters become plugins. Warden Epic 9 and peer station process stories consume this contract.
**FRs covered:** canopy:FR-43, canopy:FR-45 (canopy:FR-44 is Warden Epic 9)

## Epic 18: Chrome and the trusted client

An operator installs one package and every portal looks like the estate. Services independently verify who called them. Lands in `django-pyforge` (canopy:AD-1, canopy:AD-3, canopy:AD-7). No `pyforge.*` import under `src/platform/` (parent AD-2).

### Story 18.1: django-pyforge is the only chrome

As a portal author,
I want one installable chrome package with an AppConfig registration protocol,
So that adding a station does not edit the host URLconf or ship a second switcher.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** canopy:FR-1, canopy:FR-2 • canopy:AD-1, canopy:AD-3
**Given** two portal apps in `INSTALLED_APPS` **When** they render a page **Then** chrome markup is byte-identical and sourced from `django-pyforge`
**And** a test that enumerates portal template/static dirs **fails** if either ships a base layout, switcher, or theme copy
**And** discovery is `apps.get_app_configs()`; host URLconf has no station roster except the later `/compliance/` redirect
**And** a portal registering outside `/stations/<name>/` fails the check
**And** AppConfig / discovery carries owner slug, backup, `work_class`, and promotion date; SLA body is not a chrome field
**And** removing `django-pyforge` from `INSTALLED_APPS` breaks both portals identically

### Story 18.2: The switcher shows only what the user may reach

As a signed-in operator,
I want the app switcher to list only stations my IdP roles permit,
So that I am not offered doors I cannot open.

**Type:** feature • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** canopy:FR-3 • canopy:AD-15
**Given** a user lacking a station role **When** they load chrome **Then** that station is absent from the switcher
**And** requesting the hidden station URL directly is still refused by that station (switcher is not enforcement)
**And** roles are re-read from the token on the request, not a durable local grant

### Story 18.3: Two clients, one RS256 assertion

As a station service,
I want every portal and CLI call to carry the same audience-bound JWT,
So that I can verify the end user without trusting a header.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** canopy:FR-14, canopy:FR-15 • canopy:AD-7
**Given** the golden vector in `django-pyforge` **When** both the portal client and `pyforge.core` client emit a token **Then** both pass the same RS256 verification (`sub`, `roles`, `aud=mcp:<station>`, `exp`≤5m from `iat`, `delegated_by=pyforge-host`)
**And** a call with a bad signature, wrong audience, or expired `exp` is refused
**And** a request with an identity header and no valid assertion is refused
**And** HMAC-SHA256 and laptop-minted secrets are absent
**And** a portal constructing a raw HTTP request to a service is a review-blocking finding

## Epic 19: Eight portals, one prefix

Operators move between stations without changing origin. Warden relocates before Liquibase revokes app-role DDL (canopy:FR-9b sequencing).

### Story 19.1: Warden moves and is renamed

As a compliance auditor,
I want Warden at `/stations/warden/` with `/compliance/` still working,
So that bookmarks survive the uniform prefix.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** canopy:FR-9a, canopy:FR-9b • canopy:AD-2, canopy:AD-4
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

**Type:** feature • **Effort:** L • **Deps:** S-19.1, S-18.3 • **FR/AD:** canopy:FR-9, canopy:FR-10 • canopy:AD-2, canopy:AD-18
**Given** chrome and the assertion client **When** I request each of the eight portals in one session **Then** none re-authenticate and all are same-origin with Lane 1
**And** each remaining station has `django-<station>/` with the naming triple; existing models do not move between apps
**And** portals reach stations only through `django-pyforge`'s client; no portal imports station internals or builds raw HTTP to a service
**And** portal Django models are projections, not a second write path
**And** the switcher does not tile a `work_class` 01 or 02 registration as a first-class station

## Epic 20: The published front door

Wagtail at `/` supersedes the static console *as the front door*; removal of the old pipeline is Epic 30.

### Story 20.1: Wagtail publishes without a deploy

As an editor,
I want to change a page and have it live without a rollout,
So that runbooks do not wait on a deploy.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** canopy:FR-4, canopy:FR-5 • canopy:AD-13
**Given** an authenticated editor with the Wagtail-admin IdP group **When** they publish a page **Then** an estate request sees it with no new image and no Deployment rollout
**And** content survives pod restart and is identical from every replica
**And** unauthenticated admin requests redirect to the IdP; no local password or email-management surface is reachable
**And** an authenticated user with no admin group is refused with a comprehensible error

### Story 20.2: Media, renditions, and a cache that cannot eat the queue

As an operator,
I want uploaded media on shared storage and a cache that cannot evict Celery,
So that scaling Lane 1 does not lose files or drop builds.

**Type:** feature • **Effort:** L • **Deps:** S-20.1 • **FR/AD:** canopy:FR-8, canopy:FR-30 • canopy:AD-13, canopy:AD-10 • NFR-C7
**Given** a ReadWriteMany PVC for Wagtail media and two Redis Deployments **When** replica A stores an upload **Then** replica B retrieves it
**And** a rendition generated on A is served from redis-cache by B without regeneration
**And** filling redis-cache to eviction loses no queued task on redis-broker
**And** Celery and Channels use the broker; Django cache + Wagtail renditions use the cache
**And** independent scale of work is a Celery worker Deployment — not a second public ASGI process
**And** no Lane 1 state lives on ephemeral pod disk; MinIO/S3 is a review-blocking finding
**And** search is PostgreSQL FTS; Wagtail background work uses in-tree Celery `BaseTaskBackend` (not django-tasks DB/RQ, not `django-tasks-celery`)

## Epic 21: Agents survive; run state is a service

`start_*` is a supervisor publish (canopy:AD-12). Handles live in `public.mcp_handles`; runs in `public.run_state`.

### Story 21.1: Supervisor tables in public

As an agent,
I want handles and run rows in PostgreSQL owned by `django-pyforge`,
So that any replica can answer `get` and the front door never reads a laptop disk.

**Type:** feature • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** canopy:FR-12, canopy:FR-40 • canopy:AD-6, canopy:AD-9, canopy:AD-12
**Given** the platform database **When** this story lands **Then** `run_state` and `mcp_handles` exist as tables in `public`, not new schemas
**And** DDL is authored as Django migrations owned by `django-pyforge` (Epic 27 will extract changesets)
**And** no front-door or MCP path reads `~/.bmad-loops`, tmux, or journals

### Story 21.2: Atlas MCP on the host, dual-era

As an autonomous agent,
I want atlas's service face on `POST /stations/atlas/mcp` using the official `mcp` SDK,
So that handshake-era and modern clients both work.

**Type:** feature • **Effort:** L • **Deps:** S-18.1, S-18.3 • **FR/AD:** canopy:FR-11 • canopy:AD-5
**Given** the host ASGI process **When** a client posts to `/stations/atlas/mcp` **Then** the face speaks MCP revisions `2025-03-26` through `2026-07-28`
**And** handshake `initialize` echoes the client's requested revision; unsupported revisions return `-32022` with the supported list
**And** no code path branches on client name or user-agent; deprecated dual-endpoint SSE is not served
**And** atlas's existing server is brought to this spec, not duplicated
**And** the `local-recipes` stopgap (`fastmcp>=3.4.7,<4` + `mcp>=1.24,<2.0`) lifts its `mcp` ceiling in this story if the platform env can take `mcp>=2.0`

### Story 21.3: start/get survives disconnect

As an autonomous agent,
I want a multi-minute operation to return a handle immediately and be fetchable after a drop,
So that a 30s idle timeout does not lose the work.

**Type:** feature • **Effort:** L • **Deps:** S-21.1, S-21.2 • **FR/AD:** canopy:FR-12 • canopy:AD-6, canopy:AD-12
**Given** a simulated ingress disconnect mid-operation **When** the client reconnects with the handle and a valid assertion **Then** it receives the same result without recomputation
**And** `start_*` returns before the work finishes and publishes through the supervisor (no second ledger)
**And** `get_*` succeeds on a different replica; possession of the handle without the assertion is refused
**And** handles are opaque, high-entropy, and TTL'd; progress notifications / sticky sessions / stream replay are not the survival mechanism

### Story 21.4: The other seven MCP faces

As an autonomous agent,
I want every station on the same POST pattern,
So that I do not learn eight transports.

**Type:** feature • **Effort:** L • **Deps:** S-21.3 • **FR/AD:** canopy:FR-11 • canopy:AD-1, canopy:AD-5
**Given** the atlas face **When** the remaining seven stations register MCP tokens **Then** `POST /stations/<name>/mcp` conforms to the same dual-era checks
**And** host dispatch is a pattern, not a per-station list

### Story 21.5: Front door queries the supervisor

As a platform operator,
I want live runs and completed timing from the supervisor,
So that the published board is not `unavailable` for lack of my home directory.

**Type:** feature • **Effort:** M • **Deps:** S-21.1 • **FR/AD:** canopy:FR-40, canopy:FR-41, canopy:FR-42 • canopy:AD-12, canopy:AD-15
**Given** a deployed egress-blocked namespace **When** the front door renders run state **Then** it uses the supervisor API only — no filesystem fallback
**And** a run started on one machine is visible to a front door on another
**And** timing is ingested at run completion, queryable across runs
**And** an unreachable supervisor renders explicit unavailable plus age, within the canopy:FR-26 budget — not an empty list presented as current

## Epic 22: One command grammar

### Story 22.1: pyforge dispatches without reimplementing

As a packaging engineer,
I want `pyforge <station> <noun> <verb>` to match each station binary,
So that I do not memorize eight CLIs.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** canopy:FR-13 • canopy:AD-14
**Given** the eight station console scripts **When** CI generates the parity matrix **Then** every verb is reachable through both paths
**And** adding a station verb that the unified entry cannot reach fails the build
**And** no station logic is copied into `pyforge-core`; dispatch only
**And** a station CLI that cannot be introspected gets a named preparatory story rather than a silent skip

## Epic 23: Boards show only your rows

### Story 23.1: Same URL, different rows

As a compliance auditor,
I want analytical boards behind the host to filter rows by my role,
So that I never see another tenant's slice.

**Type:** feature • **Effort:** L • **Deps:** S-18.2, S-19.2 • **FR/AD:** canopy:FR-16 • canopy:AD-20
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

**Type:** feature • **Effort:** L • **Deps:** S-20.2 • **FR/AD:** canopy:FR-17, canopy:FR-18 • canopy:AD-8
**Given** a consumer that is down **When** an event is `XADD`ed to `pyforge.events` **Then** it is delivered on return without double-apply
**And** a malformed event lands in `pyforge.events.dlq` via `XAUTOCLAIM` and does not block the group
**And** an operator can enumerate quarantined messages
**And** producers never write to redis-cache; `dataschema` is required
**And** the envelope carries `spec_id`, git sha, and SBOM purl, plus an optional work-item id; a missing Jira key is not a fail

### Story 24.2: Cascades halt; adapters validate

As a platform operator,
I want cyclic fan-out to stop at depth 8,
So that a buggy producer cannot run away.

**Type:** feature • **Effort:** M • **Deps:** S-24.1 • **FR/AD:** canopy:FR-19, canopy:FR-20 • canopy:AD-8
**Given** a deliberate cycle **When** `pyforgeloopdepth` reaches 8 **Then** publish halts observably
**And** event `type` is a dotted verb registered in `django-pyforge`
**And** payload shape is rejected in the consuming domain adapter, not at the stream boundary

## Epic 25: Failure stays contained

Each invariant has a test that fails with the mechanism absent (canopy:AD-15).

### Story 25.1: Circuits trip on async too

As an operator,
I want a dead dependency to degrade the caller,
So that one outage does not hang the estate.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** canopy:FR-26 • canopy:AD-15
**Given** repeated outbound failures **When** the circuit opens **Then** the caller returns degraded within budget
**And** a failing asyncio call registers as a failure (in-tree PyBreaker wrapper), not a success
**And** `fail_max` is coarse, never exact-count
**And** removing the wrapper makes the test fail

### Story 25.2: One DuckDB writer

As an atlas consumer,
I want a single writer on `atlas.duckdb`,
So that concurrent connects cannot corrupt it.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** canopy:FR-27 • resilience BS-5
**Given** a live `atlas.duckdb` **When** a second writer appears **Then** it is refused or serialized
**And** readers use `read_only=True`
**And** the test fails if the boundary is removed

### Story 25.3: Validation errors render inline

As an operator on an HTMX form,
I want 422 arrays as Django `ValidationError`s,
So that I see field errors in place.

**Type:** feature • **Effort:** S • **Deps:** S-18.1 • **FR/AD:** canopy:FR-28 • resilience BS-7
**Given** a rejected submission **When** the response renders **Then** errors appear inline on the originating surface
**And** `PydanticFormErrorBridge` lives in `django-pyforge`
**And** the test fails if the bridge is removed

### Story 25.4: Restarts reconcile

As a mason operator,
I want a killed boot to re-index without duplicating rows,
So that restarts are safe.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** canopy:FR-29 • resilience BS-8 • canopy:AD-13
**Given** work interrupted mid-flight **When** the process restarts **Then** the effect applies once
**And** reconcile is against PostgreSQL (and RWX files if any), **not** MinIO
**And** the test fails if reconciliation is removed

## Epic 26: Access, secrets, and flags

### Story 26.1: Revoke takes effect on the next request

As a security officer,
I want an IdP role change to apply without a re-login wait,
So that access is actually revocable.

**Type:** feature • **Effort:** M • **Deps:** S-18.2 • **FR/AD:** canopy:FR-31 • canopy:AD-15
**Given** a user who can open a portal **When** the role is revoked at the IdP **Then** the next request is denied
**And** local group tables are not the authority

### Story 26.2: Manifests carry secret references only

As a platform operator,
I want rendered Helm to contain `secretKeyRef`s and never secret values,
So that a git-diff of the chart cannot leak credentials.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** canopy:FR-32 • canopy:AD-19 • parent canopy:AD-12
**Given** `helm template` (or Kustomize) output **When** a secret check runs **Then** it fails if a secret *value* appears
**And** pods consume env/file mounts; the app does not call a secrets HTTP API
**And** Vault injector / CSI / extra secrets sidecar is out of this chain without a dated Dream entry

### Story 26.3: OpenFeature packages on the channel (operator gate)

As a platform operator,
I want flag libraries from conda-forge,
So that CAP-13 can evaluate offline.

**Type:** chore • **Effort:** — • **Deps:** — • **FR/AD:** canopy:FR-33 • canopy:AD-16
**Blocked:** operator-owned packaging (`openfeature-sdk`, `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`, `cachebox` 5.x). This story does **not** author recipes.
**Given** those packages on the platform channel **When** the env solves **Then** S-26.4 may start
**And** until then S-26.4 stays blocked

### Story 26.4: One flag flips three surfaces without a redeploy

As a platform operator,
I want to change one JSON flag and see Django, MCP, and CLI obey,
So that behaviour flips in an air gap without a rollout.

**Type:** feature • **Effort:** L • **Deps:** S-26.3 • **FR/AD:** canopy:FR-34 • canopy:AD-11
**Given** one JSON tree (ConfigMap from `src/platform/config/flags.json`) **When** a flag value changes on disk **Then** all three surfaces observe it with no egress
**And** the in-process FILE provider watches the mount — no Deployment rollout, no Reloader, no flagd sidecar
**And** two trees is a review-blocking finding
**And** CLI uses the same bytes (host fetch or local-dev file)

## Epic 27: Schema change is governed

**HARD:** S-19.1 (canopy:FR-9b) before any story here that revokes app-role DDL.

### Story 27.1: Liquibase on the channel (operator gate)

As a platform operator,
I want Liquibase 5.0.4+ inside the platform image,
So that production DDL has an auditable tool.

**Type:** chore • **Effort:** — • **Deps:** — • **FR/AD:** canopy:FR-21 • canopy:AD-16
**Blocked:** operator-owned packaging (`liquibase` ≥5.0.4, vendored PostgreSQL JDBC, no new image). This story does **not** author recipes.
**Given** the package on the channel the platform env consumes **When** the env solves **Then** S-27.2 may start

### Story 27.2: Pre-upgrade Job and DML-only app role

As an auditor,
I want schema change applied by a migration role before pods start,
So that the application cannot ALTER itself.

**Type:** feature • **Effort:** L • **Deps:** S-27.1, S-19.1 • **FR/AD:** canopy:FR-21a, canopy:FR-22, canopy:FR-24 • canopy:AD-9
**Given** a chart upgrade **When** hooks run **Then** Job weight −1 runs `liquibase update` on the platform image, then the shipped Job runs `migrate --fake`
**And** `preserveSchemaCase` is off; schema names lowercase; Job connects directly with `currentSchema`, not through a pooling proxy
**And** schemas are exactly `public`, `langflow_schema`, `dbgpt_schema`, `liquibase`
**And** app role `CREATE`/`ALTER`/`DROP` is refused by PostgreSQL; no init container
**And** changeset ids are `distribution:seq`

### Story 27.3: Stale extraction fails CI

As a developer,
I want a model change without a changeset to break the build,
So that production DDL cannot drift from what was reviewed.

**Type:** feature • **Effort:** M • **Deps:** S-27.2 • **FR/AD:** canopy:FR-23 • canopy:AD-9
**Given** a model change with no matching Liquibase changeset **When** CI runs `sqlmigrate` extraction **Then** the check fails and names the missing changeset

### Story 27.4: Test databases still migrate

As a developer,
I want `manage.py test` unchanged,
So that governed production DDL does not capture ephemeral DBs.

**Type:** chore • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** canopy:FR-25
**Given** the test runner **When** it creates a test database **Then** it still runs Django `migrate`
**And** no test-suite rewrite is required by this epic

## Epic 28: Scribe's graph outlives a file

### Story 28.1: PostgreSQL driver behind the existing port

As a steward operator,
I want the graph store on PostgreSQL/pgvector with a local path remaining,
So that the JSON file is not the production backend.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** canopy:FR-35 • parent AD-1, parent AD-5
**Given** the existing `GraphStore` port **When** the suite runs **Then** it passes against both the durable driver and the local path
**And** callers do not branch on which driver is active
**And** concurrent writers do not corrupt the durable store

### Story 28.2: Semantic recall

As an agent,
I want recall that matches meaning, not only tokens,
So that I find nodes lexical overlap misses.

**Type:** feature • **Effort:** M • **Deps:** S-28.1 • **FR/AD:** canopy:FR-36
**Given** a target with no lexical overlap **When** semantic recall runs **Then** it returns that target
**And** the lexical path does not

## Epic 29: Every 03 station is five tiers

### Story 29.1: SKF domain skills from station packages

As an autonomous agent,
I want a version-pinned skill compiled from `pyforge-<station>/`,
So that I follow how the station actually works.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** canopy:FR-37 • canopy:AD-17
**Given** a station that has no skill today **When** SKF compiles from `src/shared/packages/pyforge-<station>/` **Then** an agent loads that skill and follows it on the station's core task
**And** output is agentskills.io-compliant with provenance; `skf-export-skill` is the only write into `CLAUDE.md` / `AGENTS.md`
**And** `conda-forge-expert` is not replaced

### Story 29.2: Personas act only through grammar and MCP

As an operator,
I want each station addressable as a persona,
So that an agent does not freelance against the filesystem.

**Type:** feature • **Effort:** L • **Deps:** S-22.1, S-21.4, S-29.1 • **FR/AD:** canopy:FR-38 • canopy:AD-14, canopy:AD-17
**Given** a station persona **When** it completes a station task **Then** the transcript shows only canopy:FR-13 grammar and canopy:FR-11 MCP — no direct filesystem and no ad-hoc HTTP
**And** personas are BMAD launcher/agent skills that consult the CAP-15 content skill

### Story 29.3: Five-tier check

As a platform operator,
I want completeness to fail CI when a tier is missing,
So that "done" cannot mean CLI-only.

**Type:** chore • **Effort:** S • **Deps:** S-29.2 • **FR/AD:** canopy:FR-39 • canopy:AD-14
**Given** all eight **03** stations **When** the check runs **Then** it reports each of CLI, portal, service, skill, persona
**And** declaring an **03** station complete with fewer than five fails the check
**And** 01/02 fixtures (spec+script or spec+skill only) do not fail the check

## Epic 30: The old console is gone

canopy:FR-6 inventory is done. Parity build uses Epic 20 + Epic 21.5. Kedro-Viz is not in scope for deletion.

### Story 30.1: Remaining console surfaces have a home

As a platform operator,
I want every runtime-reproducible console view to exist on Lane 1 or a portal,
So that deletion does not drop a live surface.

**Type:** feature • **Effort:** L • **Deps:** S-20.1, S-21.5 • **FR/AD:** canopy:FR-6, canopy:FR-7 • console-parity-inventory
**Given** the 23-surface inventory **When** this story completes **Then** each runtime-reproducible and mixed surface has a named Canopy home
**And** detector verdicts are a scheduled job, cached result, visible age
**And** editorial content is CMS (Epic 20)
**And** live run state and timing come from the supervisor (S-21.5)

### Story 30.2: Delete the generator and its inbound refs

As a platform operator,
I want the old build path gone, not unlinked,
So that two consoles cannot become permanent.

**Type:** chore • **Effort:** L • **Deps:** S-30.1 • **FR/AD:** canopy:FR-7
**Given** proven parity **When** this story merges **Then** the generator, its four pixi tasks, scheduled workflow trigger, and committed data blob are gone
**And** inbound refs (docs, workflows, specs, presentations, scripts, tests — 100+ including the Charter gate) no longer 404 or point at the retired path
**And** the Kedro-Viz tree and its workflow survive
**And** `spec-factory-console` is marked superseded (Marshal Phase 5 records the same retirement)
**And** downstream parsers of the data blob are migrated first

## Canopy obligations (2026-08-24)

**Owner:** `pyforge-steward` owns the Canopy (`src/platform/` host + residual CAP-1..145 over
shipped python-agent-platform work). The Canopy is not a ninth station.

**Build surface:** Epics 18–30 (appended above) are the steward implementation chain for
`spec-pyforge-unifying-strategy`. Cite **parent AD-n** (`spec-python-agent-platform` spine)
vs **canopy AD-n** (`architecture-pyforge-unifying-strategy-2026-08-24`); bare `AD-n` is
review-blocking.

**Shipped work stands:** Epic 11 (Stories 11.1–11.4) remains **done**. Schema isolation
(`langflow_schema`, `dbgpt_schema`, `search_path`, Pattern A/B) is not reopened. canopy:FR-22 / canopy:AD-9 supersedes only the **production DDL mechanism** — Epic 27, not a rollback of Epic 11.

**Sequencing:** S-19.1 (canopy:FR-9b) before Epic 27 stories that revoke app-role DDL. S-26.3 and
S-27.1 stay **blocked** on operator-owned packaging (canopy:AD-16).

**Phase 5 scope:** This block records steward obligations. Peer stations (atlas, marshal,
warden, doctor, herald, mason, scribe) run their own Phase 5 course-correction proposals;
Marshal additionally retires `spec-factory-console`. Open question `lane1-serves-dw-h3` stayed
joint with atlas — **answered no 2026-08-25** (Wagtail `/cms/` ≠ La Suite Docs REST); not a
steward story.

## Epic 31: Non-module suite pieces install by class

**Spec binding.** Decomposes `spec-bmad-suite-install-class-wiring` CAP-1..145 (Spec landed
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

## Epic 32: One plugin API for eight stations

Canopy Epics 18–30 do not implement CAP-18. This epic is the shared contract (canopy:FR-43) plus
steward's own process retrofit (canopy:FR-45). Warden Epic 9 implements canopy:FR-44. Peer stations
mint their own process-hook stories that **depend on S-32.1**. Lands in existing
`pyforge-core` (marshal Epic 14 floor); steward owns the Canopy FR. **Not a scorecard.**

### Story 32.1: Shared hook-spec and plugin registration in pyforge-core

As a station author,
I want one registration API and one hook-spec documentation shape,
So that eight stations do not invent eight plugin APIs.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** canopy:FR-43 • canopy:AD-21 • CAP-18
**Surface:** `pyforge-core` (shared floor; do not add a ninth package)
**Given** a dummy plugin declared against the published API **When** the loader runs **Then** the plugin is invoked at a named before/after/around (or equivalent documented) point
**And** a conformance check **fails** if a station package ships a parallel registration mechanism for the same class of extension
**And** the contract documents that a plugin must not publish a second verdict for a process another owner specified
**And** Pixi task names, Golden Path artifact identity, parent infra kinds, host import boundary, and the Warden verdict itself are listed as **not** plugin surfaces

### Story 32.2: Steward deploy-profile adapters are plugins

As a platform operator,
I want Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, and Jira as deploy-profile plugins,
So that swapping a vendor does not fork the Golden Path.

**Type:** feature • **Effort:** M • **Deps:** S-32.1 • **FR/AD:** canopy:FR-45 • canopy:AD-21
**Given** today's deploy/profile backends **When** they are extracted **Then** each registers as a default plugin on the canopy:FR-43 contract
**And** disabling an optional vendor plugin does not fail the Golden Path Pixi task
**And** Tachyon remains a production LLM **adapter** plugin — local/CI must not require it
**And** none of these plugins publishes a PR quality-gate verdict

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (canopy:AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Steward-local:** Deploy-profile adapters (Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, Jira) are **steward hook plugins** on the Golden Path (Stories **32.1–32.2**), not core stack and not a second PR gate. Canopy Epics 18–30 stay chrome/portals/MCP/DDL and must not violate CAP-18. **Epic 33** is station-owned skill/persona + first portal job — not a Canopy remint.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`;
`change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md`.

## Epic 33: Steward owns its skill, persona, and one portal job

Steward Epic 29 proved the SKF+persona *shape* and the five-tier reporter. Epic 19 shipped an empty `/stations/steward/` shell. This epic does **not** copy Canopy 18–30 and is **not** appended to that list.

### Story 33.1: SKF domain skill and BMAD persona for steward

As an autonomous agent,
I want a steward SKF skill compiled from `pyforge-steward/` and a `bmad-agent-steward` persona,
So that Path B uses this station's grammar and MCP instead of freelancing the filesystem.

**Type:** feature • **Effort:** L • **Deps:** S-32.1, S-29.3 • **FR/AD:** canopy:FR-37, canopy:FR-38 • canopy:AD-17
**Given** steward 29.1/29.2 proved the shape on one station **When** this story completes **Then** `.claude/skills/pyforge-steward/` exists (SKF from `src/shared/packages/pyforge-steward/`) with provenance
**And** a BMAD persona consults that skill and uses only CAP-5 `pyforge steward …` and CAP-4 `POST /stations/steward/mcp`
**And** `conda-forge-expert` is not replaced
**And** `skf-export-skill` is the only write into `CLAUDE.md` / `AGENTS.md`

### Story 33.2: First portal slice — provision inventory

As a platform operator,
I want `GET /stations/steward/` to show the named pixi environments (`provision --list`),
So that one operator job works in HTMX without leaving the host session.

**Type:** feature • **Effort:** M • **Deps:** S-33.1, S-19.2 • **FR/AD:** FR-10 • canopy:AD-7
**Given** an authenticated steward-role session **When** the operator opens `/stations/steward/` **Then** HTMX renders the environment inventory from the station via `django-pyforge`'s PortalClient only
**And** no raw HTTP, no `pyforge.*` import under `src/platform/`, no chrome copy in `django-steward`

## Epic 34: One query plane (CAP-19)

Canopy residual after CAP-1..145 closeout. Atlas owns the engine; stations rebuild onto it.
Do not re-dispatch 18–32. Defaults: in-process DuckDB; named new Atlas pipeline; Scribe
store-port driver on the plane (34.5). Story spec for 34.1 is tracked.

### Story 34.1: Read-only live attach

As an operator,
I want DuckDB to attach a fixture multi-schema Postgres read-only,
So that Mode A answers without writing OLTP or installing `pgvector`.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** canopy:FR-46 • canopy:AD-22
**Given** a fixture Postgres with two schemas and no `pgvector` **When** the plane attaches **Then** a federated read succeeds and a write is refused
**And** the path is not pandas `SQLQueryDataSet`
**And** consumer boot does not `INSTALL` extensions

### Story 34.2: Kedro writes the Parquet cache

As an operator,
I want a named Kedro pipeline to extract heavy tables to compressed Parquet,
So that dashboards and autonomous SQL hit the cache.

**Type:** feature • **Effort:** M • **Deps:** S-34.1 • **FR/AD:** canopy:FR-47 • canopy:AD-22
**Given** the named pipeline **When** `kedro run` completes **Then** the Parquet cache exists
**And** a scan of it does not use the OLTP writer role
**And** refresh is not Airflow and not an `01_raw` folder tree

### Story 34.3: Vectors persist on the plane

As an agent,
I want HNSW ranking on the plane writer,
So that RAG does not use a second `.duckdb` or an in-memory default.

**Type:** feature • **Effort:** L • **Deps:** S-34.2 • **FR/AD:** canopy:FR-48, FR-27 • canopy:AD-22
**Given** `REAL[]` (or equivalent) rows **When** the extract runs **Then** `FLOAT[N]` + `vss` nearest-neighbor returns the planted row
**And** the writer is the CAP-19 plane (FR-27)
**And** the consumer only `LOAD`s `vss`
**And** Atlas in-memory RAG default is replaced or injected through that writer

### Story 34.4: Agents cannot reach OLTP

As a platform operator,
I want DB-GPT and Langflow estate reads pointed at the plane,
So that hallucinated SQL cannot hit the system of record.

**Type:** feature • **Effort:** M • **Deps:** S-34.2 • **FR/AD:** canopy:FR-49 • canopy:AD-22
**Given** platform Langflow / DB-GPT config **When** the gate runs **Then** the estate read DSN is the plane (cache / views / optional HTTP face)
**And** an OLTP DSN for Text-to-SQL fails the test

### Story 34.5: Scribe semantic recall uses the plane

As a teammate,
I want `scribe recall --semantic` to rank on the plane behind the store port,
So that canopy:FR-36 survives the rebuild.

**Type:** feature • **Effort:** L • **Deps:** S-34.3 • **FR/AD:** canopy:FR-50, canopy:FR-36 • canopy:AD-22
**Given** the durable driver **When** semantic recall runs **Then** a no-overlap query still hits
**And** callers do not `isinstance` the driver
**And** lexical recall is unchanged
**And** a private Chroma / in-memory DuckDB path fails the test

## Epic 35: Cluster requires mcp-host (spec-mcp-era-isolation CAP-4)

Slice 1 shipped the bridge. This epic fail-louds the **cluster** overlay so
mcp-host cannot be omitted. Not CAP-19. Not slice 3. First query-plane dispatch
stays 34.1; this story is serial after that session (no code dep).

### Story 35.1: Cluster requires mcp-host

As a platform operator,
I want the Helm chart and production check to refuse a cluster without mcp-host,
So that host MCP cannot silently degrade to the ImportError skip on CRC.

**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** spec-mcp-era-isolation CAP-4
**Given** `helm template` with an empty `mcpHost.image.repository` **When** it runs **Then** it fails
**And** there is no `mcpHost.enabled` knob
**And** production/cluster `manage.py check` errors if `MCP_HOST_SIDECAR_BASE_URL` is unset
**And** laptop URL-unset + ImportError skip still boots
**And** sidecar down is 502 on `/stations/<name>/mcp`, not a web CrashLoop

## Epic 36: Lane 3 Vizro over the estate cache

Canopy residual after CAP-19. Vizro stays isolated (CAP-7). BSL is the
metric contract. Do not import Vizro into Django. Not vizro-ai.

### Story 36.1: Lane 3 BSL reads the estate cache

As an operator,
I want BSL to query the named estate Parquet cache,
So that Lane 3 dashboards do not hit OLTP.

**Type:** feature • **Effort:** S • **Deps:** S-34.2 • **FR/AD:** canopy:FR-47 • canopy:AD-22
**Given** the 34.2 Parquet cache **When** the BSL model queries it **Then** planted rows return
**And** the loader does not use an OLTP writer role

### Story 36.2: Estate cache Vizro page

As an operator,
I want a Lane 3 page for the estate Parquet cache,
So that the BSL loader is actually on a board.

**Type:** feature • **Effort:** S • **Deps:** S-36.1 • **FR/AD:** canopy:FR-47 • canopy:AD-22
**Given** `build_dashboard` **When** it runs **Then** page `estate-cache` exists with a stable id and title
**And** a planted cache query matches an independent BSL model
**And** Django does not import Vizro

## Epic 37: Five-tier roster drain

The eight 03 stations are complete. Mason's skill cell is `conda-forge-expert`
(Epic 11: CFE stays). Declaring the roster complete makes a missing cell fail CI.

### Story 37.1: Declare eight stations five-tier complete

As a platform operator,
I want the five-tier check to treat the roster as complete,
So that a missing CLI, portal, service, skill, or persona fails CI.

**Type:** chore • **Effort:** S • **Deps:** S-29.3 • **FR/AD:** canopy:FR-39 • canopy:AD-14
**Given** the eight roster stations **When** the check runs **Then** every cell is present
**And** mason's skill cell is `conda-forge-expert` (no `pyforge-mason/` skill)
**And** `DECLARED_COMPLETE` is the full roster

## Epic 38: Factory stdio MCP translator (spec-mcp-factory-stdio-translator)

**Retroactive.** Slice 1 (the CRC gunicorn sidecar bridge) shipped `#858`; the operator
scheduled slice 2 the same day, 2026-08-26, and it shipped `ba4ae74f73` within that
session — but no story was ever written for it, so `chain-completeness` flagged the
Spec as undecomposed despite the code being real, tested, and running. This epic
documents what already exists; no new implementation.

### Story 38.1: The translator wraps a factory tool over stdio and never claims to be the CRC fix

As an MCP client operator,
I want a stdio process that speaks MCP 1.x-legal traffic to a FastMCP 3 / mcp 1.x child,
So that a modern client (no handshake, `_meta` on every call) can call a factory tool
without either SDK being loaded in the same interpreter.

**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** spec-mcp-factory-stdio-translator CAP-1, CAP-2
**Given** a modern client with no handshake **When** it calls a wrapped child **Then** the
child sees a fabricated `initialize` handshake and every `_meta` key is stripped before
the child sees the request
**And** a handshake-era client passes through without a double `initialize`
**And** a plain-text or `text`-keyed child result wraps as `content:[{type:"text",text}]`
**And** an unsupported protocol version is rejected before the child process starts
**And** `--help` and the module docstring both state this does not change gunicorn
`/stations/<name>/mcp` and does not lift `python-agent-platform` (CAP-2's non-CRC claim)
**And** the process imports neither `mcp` 1.x nor 2.x
**Status:** done — shipped `ba4ae74f73` (2026-08-26), tests in
`tests/scripts/test_mcp_factory_stdio_translator.py` (6 passed)

## Epic 39: The bmad-suite metapackage (spec-bmad-suite-metapackage)

**Retroactive decomposition.** suite:CAP-1/2/3 landed on main 2026-09-01
(manifest, metapackage recipe, CFE generator, local build, channel publish);
chain-completeness had flagged the Spec as undecomposed. suite:CAP-4 (optional
``feature.bmad-suite-full`` pixi pin) remains backlog. This epic is also the
decomposition of `spec-bmad-suite-channel-product` suite:CAP-6 (suite metapackage,
added to that Spec 2026-09-01), whose own text points here — cited so the
chain-completeness window for the channel-product Spec sees it.

### Story 39.1: Canonical suite manifest

As a factory operator,
I want a tracked ``recipes/bmad-suite/suite-members.yaml`` catalog,
So that doctor, steward pipeline-truth, and the metapackage share one population.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** suite:CAP-1
**Status:** done — shipped 2026-09-01 (``e177de648e``)

### Story 39.2: Metapackage recipe

As a factory operator,
I want a ``noarch: generic`` ``bmad-suite`` metapackage pinning every active member,
So that one channel install pulls the whole suite.

**Type:** feature • **Effort:** M • **Deps:** S-39.1 • **FR/AD:** suite:CAP-2
**Status:** done — shipped 2026-09-01

### Story 39.3: Generator and batch build

As a factory operator,
I want ``generate-bmad-suite`` / ``build-bmad-suite`` to refresh pins from registry class,
So that metapackage bumps are mechanical after member upstream moves.

**Type:** feature • **Effort:** M • **Deps:** S-39.2 • **FR/AD:** suite:CAP-3
**Status:** done — shipped 2026-09-01

### Story 39.4: Optional pixi feature bundle (suite:CAP-4)

As a greenfield operator,
I want ``feature.bmad-suite-full`` to depend on ``bmad-suite`` instead of 13 pins,
So that pixi.toml stays thin for full-suite installs.

**Type:** feature • **Effort:** S • **Deps:** S-39.3 • **FR/AD:** suite:CAP-4
**Status:** backlog

## Epic 40: Red-team CRITICALs — verified mint, durable broker (spec-pyforge-unifying-strategy CAP-6 / CAP-11)

Minted by `sprint-change-proposal-2026-09-02-red-team-critical.md` after the
2026-09-02 adversarial review (`research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`)
found two shipped CRITICALs. Additive over Epics 12 / 19 / 21 / 24; those
ledgers stay `done`. Dispatches **before** any further story on this chain
and before cutover Phase 1. The review's HIGH set (R-4 … R-16) is a later
correct-course, not this epic.

### Story 40.1: IdP bearer is verified before mint

As a platform operator,
I want `/assertion/mint/` to verify the presented IdP bearer (signature via the configured JWKS, `iss`, `aud`, `exp`) before signing a station assertion,
So that nobody can mint a valid assertion for any subject and any roles by base64-encoding a JSON payload.

**Type:** fix • **Effort:** M • **Deps:** none • **FR/AD:** CAP-6, CAP-12, canopy:FR-31 • canopy:AD-7, canopy:AD-15 • RFC-3 (revised) • red-team X-1 / R-1
**Given** the existing fake-`.sig` bearer fixture **When** it is POSTed to `/assertion/mint/` **Then** the response is 401 and nothing is minted
**And** wrong key / `alg=none` / HS256 / wrong `iss` / wrong `aud` / expired / missing claims are refused
**And** an unknown `kid` refreshes the JWKS once, never twice in the cache window
**And** a station absent from the verified group claim is 403
**And** an unconfigured verifier is 503 in every profile (local verifies against the dev JWKS file, it does not skip)
**And** production stage-1 refuses without `COMPONENT_OIDC_ISSUER` / `COMPONENT_OIDC_JWKS_URL` / `COMPONENT_OIDC_AUDIENCE`
**And** an AST policy test forbids any bearer decode outside the verifier

### Story 40.2: redis-broker is durable and bounded

As a platform operator,
I want `redis-broker` on a PVC with AOF, a required `maxmemory` below a required memory limit, no stored Celery results, and TTL on applied-id keys,
So that a broker restart loses no queued task, stream entry, pending entry, DLQ entry or idempotency key, and growth back-pressures instead of OOM-killing the pod.

**Type:** fix • **Effort:** M • **Deps:** none • **FR/AD:** CAP-8, CAP-11, canopy:FR-30 • canopy:AD-8, canopy:AD-10, canopy:AD-12, canopy:AD-15 • RFC-2, RFC-4 • red-team S-1 / A-3 / R-2 • supersedes sibling `spec-local-ocp-hybrid-environment` CAP-3 for the broker role only
**Given** `helm template` **When** rendered **Then** the broker mounts a PVC at `/data` with `--appendonly yes --appendfsync everysec --maxmemory <v> --maxmemory-policy noeviction`, and the cache is unchanged (`emptyDir`, `allkeys-lru`)
**And** an empty `redis.broker.maxmemory`, an empty broker memory limit, or `maxmemory` ≥ the limit fails the render naming the values path
**And** `CELERY_TASK_IGNORE_RESULT` is `True` and no `celery-task-meta-*` key exists after a supervised run completes
**And** `pyforge.events.applied:*` keys carry a TTL and the stream has a declared trim; the DLQ is never auto-trimmed
**And** a real `redis-server` kill/restart preserves the stream entry, the PEL entry, the DLQ and the applied key — and the test fails with `--appendonly no`
**And** the two 12.6 `emptyDir` invariants are re-scoped to the cache role

## Epic 41: Data safety (CAP-9 / CAP-10 / CAP-19)

Backups, the plane's process boundary, governed Scribe DDL, verified broker TLS. Red-team R-3, R-11, R-12, R-14.
Minted by `sprint-change-proposal-2026-09-02-red-team-high.md`; source
`research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`. Additive over shipped epics; none reopened.

### Story 41.1: DR contract and PostgreSQL backup

As a platform operator,
I want a written DR contract and a scheduled PostgreSQL base backup with WAL archiving plus a restore drill,
So that a lost volume is a recoverable incident with a known RPO/RTO, not the end of the estate.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** CAP-10, canopy:FR-29 • canopy:AD-1 (parent), canopy:AD-12 • BS-8 • red-team B-2 / S-8 / R-3
**Given** the story spec `spec-41-1-dr-contract-and-postgresql-backup.md` **When** its acceptance criteria run **Then** they pass
**And** Given `deploy/DR.md`, when read, then every store (PostgreSQL, redis-broker, redis-cache, media RWX, DB-GPT SQLite PVC, DuckDB cache) has RPO, RTO, mechanism, owner and drill cadence, and the BS-8 reconciliation order is written down.

### Story 41.2: Query-plane process boundary

As a platform operator,
I want the `.duckdb` file confined to one process on RWO storage with Parquet as the shared artifact,
So that multi-pod readers cannot corrupt or lock the query plane.

**Type:** fix • **Effort:** M • **Deps:** none • **FR/AD:** CAP-19, CAP-10, canopy:FR-27, canopy:FR-47 • canopy:AD-22 • BS-5 • red-team S-3 / R-11
**Given** the story spec `spec-41-2-query-plane-process-boundary.md` **When** its acceptance criteria run **Then** they pass
**And** Given the estate source, when the policy test runs, then every `duckdb.connect(` outside the single declared writer module passes `read_only=True` or `:memory:`; the writer module is named once in `pyforge.atlas` and the test fails if a second appears.

### Story 41.3: Scribe DDL moves into the changelog

As a platform operator,
I want Scribe's `CREATE EXTENSION` / schema / table DDL moved into a scribe-owned Liquibase changeset,
So that the DML-only app role holds in production and the auditor control is not quietly widened.

**Type:** fix • **Effort:** S • **Deps:** none • **FR/AD:** CAP-9, CAP-14, canopy:FR-22, canopy:FR-23 • canopy:AD-9 • red-team S-4 / B-1 / R-12
**Given** the story spec `spec-41-3-scribe-ddl-moves-into-the-changelog.md` **When** its acceptance criteria run **Then** they pass
**And** Given `platform_app`, when Scribe's PostgreSQL driver initialises, then it executes no DDL; a test with a DDL-revoked role passes and the relation-absent case raises a named error.

### Story 41.4: Broker TLS is verified

As a platform operator,
I want `rediss://` brokers verified against the corporate CA with `CERT_NONE` confined to the laptop,
So that an encrypted-looking broker link is actually authenticated.

**Type:** fix • **Effort:** S • **Deps:** none • **FR/AD:** CAP-12 • pap:CAP-6 (air-gap parity) • red-team X-2 / R-14
**Given** the story spec `spec-41-4-broker-tls-is-verified.md` **When** its acceptance criteria run **Then** they pass
**And** Given production settings and a `rediss://` broker, when loaded, then `ssl_cert_reqs` is `CERT_REQUIRED` and `ssl_ca_certs` points at the configured bundle.

## Epic 42: Agent and bus containment (CAP-4 / CAP-8 / CAP-11 / CAP-12)

Transport authorization, per-subject limits, real delivery semantics with a deployed consumer, Celery hardening, namespaced roles. Red-team R-7, R-8, R-9, R-10, R-13. Every story here depends on Epic 40.
Minted by `sprint-change-proposal-2026-09-02-red-team-high.md`; source
`research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`. Additive over shipped epics; none reopened.

### Story 42.1: MCP transport authorization and a streaming proxy

As a platform operator,
I want the assertion verified on every MCP JSON-RPC method before routing, a streaming proxy, and `mcp-host` reachable only from web pods,
So that no tool is reachable anonymously and long tool calls do not 502 at five seconds.

**Type:** fix • **Effort:** M • **Deps:** S-40.1 • **FR/AD:** CAP-4, CAP-6 • canopy:AD-5, canopy:AD-7 • BS-2 (revised) • red-team T-4 / T-5 / X-5 / R-7
**Given** the story spec `spec-42-1-mcp-transport-authorization.md` **When** its acceptance criteria run **Then** they pass
**And** Given `POST /stations/atlas/mcp` with no assertion, when any JSON-RPC method is sent, then 401; with a valid assertion for `mcp:warden`, then 403 on the atlas route.

### Story 42.2: Agent rate limits and run bounds

As a platform operator,
I want per-subject token buckets on the MCP route and `start`, queue and concurrent-run ceilings, and a revoke-by-subject duty,
So that a looping agent is throttled to 429 instead of taking the platform down.

**Type:** feature • **Effort:** M • **Deps:** S-40.2 • **FR/AD:** CAP-4, CAP-11, CAP-17 • canopy:AD-10, canopy:AD-12 • red-team A-6 / B-7 / R-8
**Given** the story spec `spec-42-2-agent-rate-limits-and-run-bounds.md` **When** its acceptance criteria run **Then** they pass
**And** Given one `sub` issuing more than the configured rate, when it calls the MCP route, then 429 with `Retry-After` and a structured log; other subjects are unaffected.

### Story 42.3: Bus delivery semantics and a deployed consumer

As a platform operator,
I want attempt-counted retries with backoff, DLQ for well-formed failing events, a deployed consumer per station, and `traceparent` on the envelope,
So that Warden → Doctor → Mason actually fires, poison events quarantine, and a chain is traceable end to end.

**Type:** fix • **Effort:** M • **Deps:** S-40.2 • **FR/AD:** CAP-8, canopy:FR-20 • canopy:AD-8 • RFC-4 • red-team A-1 / A-2 / A-4 / A-5 / R-9
**Given** the story spec `spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md` **When** its acceptance criteria run **Then** they pass
**And** Given a well-formed event whose handler raises N times, when consumed, then it is moved to the DLQ with the last error and ACKed; the CAP-8 success clause test (poison lands in DLQ instead of retrying forever) exists and fails without the change.

### Story 42.4: Celery hardening and the builds pool

As a platform operator,
I want `acks_late`, per-station queues, and a dedicated `builds` pool with an hours-scale limit,
So that a killed worker re-runs its task and a rattler-build is not cut off at five minutes.

**Type:** fix • **Effort:** M • **Deps:** S-40.2 • **FR/AD:** CAP-11, CAP-17 • canopy:AD-10, canopy:AD-12 • red-team S-2 / T-6 / R-10
**Given** the story spec `spec-42-4-celery-hardening-and-the-builds-pool.md` **When** its acceptance criteria run **Then** they pass
**And** Given a worker killed mid-task, when a replacement starts, then the task re-runs exactly once (acks_late + reject_on_worker_lost) and the supervisor row reaches a terminal state.

### Story 42.5: Role namespaces and the tenant claim

As a platform operator,
I want prefixed capability, tenant and admin roles with bare station names refused, and `tenant` on runs and events,
So that an IdP group that merely shares a station name cannot grant access.

**Type:** fix • **Effort:** M • **Deps:** S-40.1 • **FR/AD:** CAP-7, CAP-12, canopy:FR-3, canopy:FR-31 • canopy:AD-15, canopy:AD-20 • red-team X-3 / B-6 / R-13
**Given** the story spec `spec-42-5-role-namespaces-and-the-tenant-claim.md` **When** its acceptance criteria run **Then** they pass
**And** Given a group `atlas` (bare), when reachability is computed, then it is refused unless `DJANGO_PYFORGE_LEGACY_BARE_ROLES=1`, which logs a deprecation.

## Epic 43: Contracts and the document (CAP-6 / CAP-10 / Dream)

A readable Dream, a versioned station API, no self-call, CD by digest, one interpreter story. Red-team R-4, R-5, R-6, R-15, R-16.
Minted by `sprint-change-proposal-2026-09-02-red-team-high.md`; source
`research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`. Additive over shipped epics; none reopened.

### Story 43.1: Split the Dream into living and archive

As a platform operator,
I want the historical topology moved to an archive file and a living Dream of at most 400 lines,
So that an implementer can read the Dream and build the right thing.

**Type:** docs • **Effort:** S • **Deps:** none • **FR/AD:** Dream Grounding • red-team B-10 / R-4
**Given** the story spec `spec-43-1-split-the-dream.md` **When** its acceptance criteria run **Then** they pass
**And** Given the living Dream, when counted, then it is ≤ 400 lines and every mermaid in it is a build target.

### Story 43.2: Station API contract and the /api/v1 collision

As a platform operator,
I want `/stations/<name>/api/v<N>/` routes, OpenAPI per station, `pyforge.core.client`, and a kit contract test,
So that portals, the CLI and agents share one versioned contract and `/api/v1` no longer lands on Langflow.

**Type:** feature • **Effort:** L • **Deps:** none • **FR/AD:** CAP-6, CAP-10, canopy:FR-28 • canopy:AD-7 • BS-7 • red-team T-2 / B-3 / R-5
**Given** the story spec `spec-43-2-station-api-contract.md` **When** its acceptance criteria run **Then** they pass
**And** Given `/api/v1/anything`, when requested, then it is no longer Langflow; `/langflow/api/v1/...` still is, with the same prefix-preserving redirect behaviour.

### Story 43.3: In-process station port, no self-call

As a platform operator,
I want co-located portals reaching station code in-process and over HTTP only when `STATION_REMOTE=1`,
So that a portal view never awaits its own gunicorn pool while holding a transaction.

**Type:** fix • **Effort:** M • **Deps:** S-43.2 • **FR/AD:** CAP-6, CAP-10, canopy:FR-26 • canopy:AD-7, canopy:AD-10 • red-team T-3 / R-6
**Given** the story spec `spec-43-3-in-process-station-port-no-self-call.md` **When** its acceptance criteria run **Then** they pass
**And** Given a portal view in the default profile, when it needs station data, then no HTTP request to the host's own address is made (test asserts zero loopback calls).

### Story 43.4: Golden Path CD by digest

As a platform operator,
I want images pushed by digest, a chart that refuses `latest`, and a deploy workflow that promotes only a Warden-verdicted digest,
So that the artifact Warden passed is provably the artifact Steward deploys.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** Grounding Golden Path (Q1) • pap:CAP-6 • red-team B-4 / R-15
**Given** the story spec `spec-43-4-golden-path-cd-by-digest.md` **When** its acceptance criteria run **Then** they pass
**And** Given `helm template` with no `image.digest`/pinned tag, when rendered, then it fails naming the values path; `latest` is refused.

### Story 43.5: One interpreter story

As a platform operator,
I want the interpreter decision recorded as an AD with a measured per-environment matrix in place of the multi-Python claim,
So that the Dream states what the repo actually does and `mcp-host` has a design (MCP-SDK isolation), not an excuse.

**Type:** docs • **Effort:** S • **Deps:** none • **FR/AD:** pap:CAP-5 • spec-mcp-era-isolation • red-team S-5 / D-1 / R-16 • **decision 2026-09-02: hybrid (a)+(c)**
**Given** the solver probes of 2026-09-02 (platform feature minus langflow solves clean on 3.14; langflow blocked only by `onnxruntime <1.24`; `dbgpt-app` only by `sqlalchemy <2.0.29`) **When** the AD is written **Then** it names one interpreter `3.14.*` and states that `mcp-host` isolates `mcp` 2.x from langflow's `mcp <2` pin
**And** the Dream's multi-Python table is replaced by a table generated from `pixi.lock`
**And** the review report and readiness addendum describe the sidecar as MCP-SDK isolation

### Story 43.6: Platform image moves to Python 3.14

As a platform operator,
I want `python-agent-platform` and `dbgpt-sidecar` on `python = "3.14.*"` with a re-lock, regenerated `environment.yaml`, and rebuilt images,
So that laptop and cluster run one interpreter and Atlas/Doctor import inside the platform image.

**Type:** feature • **Effort:** M • **Deps:** S-43.5 • **FR/AD:** pap:CAP-5, pap:CAP-6 • red-team S-5 / R-16
**Cross-project gate (not a Deps edge — Marshal's parser ignores station prefixes):** Mason Epic 13, both stories (`13-1-langflow-base-onnxruntime-pin-admits-python-3-14`, `13-2-dbgpt-client-sqlalchemy-cap-admits-python-3-14`). The ledger holds `43-6` at `blocked` until both are `done`; the operator flips it to `backlog` then.
**Given** Mason 13.1 and 13.2 published **When** the pins flip and `pixi lock` runs **Then** both envs resolve on 3.14 and `environment.yaml` is regenerated in the same commit
**And** `python -c "import pyforge.atlas, pyforge.doctor"` succeeds inside the platform image
**And** `platform-ci` is green on both engines; `mcp-host` is unchanged

### Story 43.7: Sidecar runtime validation on Python 3.14

As a platform operator,
I want the `dbgpt-sidecar` image proven on 3.14 by exercising its metadata store and a real API round-trip, not by liveness alone,
So that the interpreter move is validated against work the sidecar actually does, rather than its ability to answer `/api/health`.

**Type:** feature • **Effort:** M • **Deps:** S-43.6 • **FR/AD:** pap:CAP-5, pap:CAP-6
**Re-homed 2026-09-08 from mason `DW-13-2-2`,** which deferred this validation to Story 43.6. 43.6 closed `done` without it — its acceptance criteria are the pin flip, the re-lock, the regenerated `environment.yaml` and an `import pyforge.atlas, pyforge.doctor` smoke, none of which exercise the metadata store. The work was unowned, not late.
**AC CORRECTED 2026-09-08, before implementation.** This story was first written asking for a *Celery REST round-trip*, a phrase inherited verbatim from `DW-13-2-2`'s summary. That is not achievable against this sidecar and never was: `pixi list -e dbgpt-sidecar` carries **no celery and no redis package**, the `container-dbgpt` CI job starts no broker, and `src/platform/compose/dbgpt/Containerfile` says so in its own words — *"Story 11.2/11.3 owns wiring this sidecar to real credentials and the shared Postgres/Celery surface; this story only has to make the container build, boot, and reach a healthy state on its own."* The Celery surface belongs to `python-agent-platform` (pap:AD-7, Celery over Redis) and its wiring to Stories 11.2/11.3. Writing an AC for it here would have produced a CI step that could not pass.
**The blocker that caused the original deferral is cleared.** `DW-13-2-2` recorded `dbgpt-ext-rag`'s `onnxruntime <=1.18.1` cap as having no cp314 build. Verified live 2026-09-08: `pixi list -e dbgpt-sidecar` resolves `python 3.14.7`, `dbgpt-app 0.8.2`, `dbgpt-ext-rag 0.8.2` and `onnxruntime 1.28.0 py314h112547c_0_cpu`. Nothing waits on a solve.
**Given** the `dbgpt-sidecar` container healthy on 3.14 **When** `platform-ci`'s `container-dbgpt` job runs **Then** it asserts the SQLite metadata store was really created and migrated — the database file exists at its in-container path under `$HOME/.dbgpt/workspace`, and it carries the `alembic_version` row DB-GPT's own migration writes — rather than assuming the boot sequence did it
**And** it asserts at least one real API round-trip beyond `/api/health` returns a well-formed response, so the ASGI surface is exercised and not merely alive
**And** both assertions run under docker AND podman, matching `container-dbgpt`'s existing engine matrix
**And** the Celery/Postgres half stays explicitly out of scope, owned by Stories 11.2/11.3; `mason/DW-13-2-2` records that split rather than leaving it implied

## Epic 44: Cutover to python-foundry (spec-python-foundry-cutover fnd:CAP-1 fnd:CAP-2 fnd:CAP-3 fnd:CAP-4 fnd:CAP-5 fnd:CAP-6 fnd:CAP-7 fnd:CAP-8 fnd:CAP-9 fnd:CAP-10)

The estate moves from `rxm7706/local-recipes` to `python-foundry` in six phases behind a derived move-list manifest; the recipe plant becomes the `factory/` island; `local-recipes` is archived read-only. Dream § *Cutover to `python-foundry`* (2026-09-04); spine `architecture-python-foundry-cutover-2026-09-04` (`fnd:AD-1..19`). **The cutover is a flag, not a date (`fnd:AD-17`): `local-recipes` evolves normally until `pyforge.cutover_root` flips (after 44.5); the plan regenerates or appends at will and every move is a replay (`fnd:AD-18`).**
Minted by `sprint-change-proposal-2026-09-04-foundry-cutover.md`. **Iteration 3 (`fnd:AD-20..22`): the cutover is regenerative — Dreams and memlogs seed foundry, and every capability is rebuilt or moved per the capability ledger, with the archive as oracle.** **Iteration 4 (`fnd:AD-23`, `fnd:CAP-10`): the last two open questions are closed — foundry is private permanently (`fnd:AD-14`), CI evidence is a real run with the remote host as self-hosted fallback, and 44.15 meters Actions minutes.** **Solutioning iteration 4 — every story below is ledger `blocked` until the operator flips it (`fnd:AD-9`); no story spec is drafted before that flip.** Additive over shipped epics; none reopened. Phase n ↔ Story 44.(n+3); 44.11–44.15 are enablers. **Order amended 2026-09-09
(`sprint-change-proposal-2026-09-09-currency-review.md`):** Epic 47's P1–P18 readiness lines
precede the operator's 44.3 flip (47's HARD boundary); Story 48.1 precedes any ledger write on
this project; Story 48.8 precedes the regeneration drill.

### Story 44.1: The capability ledger and the move-list manifest

As a platform operator,
I want every capability of the estate given one mode — `rebuild`, `move`, or `retire` — on scored signals, and every tracked path under a `move` capability resolved to exactly one destination,
So that realization is decided per capability and no move story can route a path twice or drop one silently.

**Type:** docs • **Effort:** M • **Deps:** S-44.13 • **FR/AD:** fnd:CAP-2 (input) • fnd:AD-1, fnd:AD-2, fnd:AD-15, fnd:AD-16 • red-team D-2 • prior art `pyforge.scribe.extras.move_list` (scribe 6.1)
**Given** `git ls-files` (rows, allowlisted trees included), `scripts/spec_surface_check.py`'s classification (owner only) and `scribe index move-list` extended with a `parent_depth` signal (coupling) **When** the manifest renders **Then** 100 % of the 24,858 tracked paths carry exactly one destination by ordered precedence, a `source_sha` and the foundry epoch SHA; a path matched by two equal-precedence rules is row kind `ambiguous` and blocks
**And** the manifest is a machine-readable file with per-directory rollups at the spine's seeded location (`docs/foundry/manifest.*`, `[ASSUMPTION]`), rows carry `kind` (`file` | `secret` | `identity`), and its row shape matches `fnd:AD-2`'s convention
**And** `steward cutover plan --regenerate` rebuilds it from scratch and `--append` folds in only the delta since the recorded `source_sha`; both preserve `moved` rows (idempotent over status)
**And** the capability ledger (`fnd:AD-2`, `fnd:CAP-9`) has one row per capability with mode, state, dependencies and the four signals scored (Spec fidelity, coupling, open debt, irreplaceable state); the first-pass modes in `cutover.md` are presented to the operator row by row, never applied silently

### Story 44.2: The red-team document fixes

As a platform operator,
I want R-23, R-24 and R-25 landed and the two stale Python-floor pins corrected,
So that the documents the cutover copies into the lasting repo state what the shipped code does.

**Type:** docs • **Effort:** S • **Deps:** none • **FR/AD:** Spec Constraints • red-team X-6 / D-5 / S-6 / T-9 • `DW-RT-2026-09-02-7/-8/-9`
**Given** the Dream, compose files and research **When** the edits land **Then** `readOnlyRootFilesystem` and the Windows / free-threading claims match the shipped Containerfile and `pixi.toml` platforms, Keycloak is pinned once at `26.4.0`, the "zero domain models" constraint reads "no station-domain models on `django-<station>`", and `stack.md` / `convergence.md` no longer pin Python `3.12.*`
**And** the three ledger entries are resolved

### Story 44.3: Open the foundry

As a platform operator,
I want `rxm7706/python-foundry` created as a fresh, recipe-free, lean-pixi estate with estate-only CI,
So that Phase 1 has a lasting root to move into.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-1 • fnd:AD-1, fnd:AD-3, fnd:AD-8, fnd:AD-9, fnd:AD-14, fnd:AD-16, fnd:AD-23 • R-17a
**Outward (`fnd:AD-9`):** creates a GitHub repository — **flipped 2026-09-13** by the operator (create the second git root; protect `main`; trunk-based from commit one). Never auto-drained.
**Given** a fresh clone **When** CI runs on the empty estate **Then** it is green, no `recipes/` directory exists, `pixi.toml` is `name = "pyforge"` with no solver-farm tooling, and `environment.yaml` is either workflow-produced or absent
**And** the repo envelope is set per `fnd:AD-14`: visibility private (permanently), `main` protected with merge commits only, secrets and vars re-provisioned through `steward keys` from manifest rows of kind `secret`, the foundry epoch SHA recorded, and `src/platform/config/flags.json` carries `pyforge.cutover_root: local-recipes` (`fnd:AD-17`)
**And** CI evidence follows `fnd:AD-23` as amended 2026-09-13 (D1): authoritative proof on this empty estate is a fresh-clone `pixi run estate-smoke` (no Helm chart yet, so no CRC). GHA (`estate.yml`) is a twin and may stay red. `steward budget check` (44.15) is not a confirmation gate
**Status:** done

### Story 44.4: Fold the packages

As a platform operator,
I want `src/shared/packages/*` under `src/packages/` in foundry with every consumer path rewritten from manifest rows and no source copied into the host image,
So that station envs solve and the host boots in foundry from workspace members.

**Type:** feature • **Effort:** L • **Deps:** S-44.3, S-44.12 • **FR/AD:** fnd:CAP-2 • fnd:AD-2, fnd:AD-3, fnd:AD-6, fnd:AD-7, fnd:AD-15, fnd:AD-18 • pap:AD-9 ratified • pap:AD-2 breach closed
**Given** the manifest rows for `src/shared/packages/**` **When** the fold lands **Then** every station env solves, the host boots, no `src/shared/` exists, the Containerfile has none of its ten `COPY src/shared/packages/...` lines and no `COPY . /app` of package source, each of the seven `django-*` packages carries a `pixi.toml` (workspace member, as the ten `pyforge-*` already do), and `five_tier.py` / `script_map_from_packages_root` / `marshal-policy.toml` / Spec `surface:` globs / CI `paths:` / the 103 `pixi.toml` path sites all point at `src/packages/`
**And** every `parent_depth` coupling row (the 59 files computing paths by `parents[N]`) is rewritten with no silent wrong-root fallback; `CLAUDE.md` / `AGENTS.md` are refreshed by `skf-export`; the affected specs are re-stamped scoped
**And** the `src/platform/ingest/github_projects/*` import of `pyforge.steward.keys` has its successor landed per `ingest-keys-import` (never deleted without one)
**And** distribution and import names are byte-identical to before the fold (package fold only — nothing from Story 44.5 rides along)
**And** the fold is `steward cutover apply --phase 1a`, re-runnable into foundry after every `--regenerate` or `--append` until the flag flips (`fnd:AD-18`)
**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch. File-move story superseded by Epic 54 / `fnd:CAP-11`. Ledger stays `backlog`. Never `apply --phase 1a` as how packages appear.
**Status:** backlog

### Story 44.5: Move the estate

As a platform operator,
I want the skills tree, the BMAD chain, the decks and the Dreams in foundry with IDE directories as symlink adapters,
So that agents and loops resolve everything from the lasting root.

**Type:** feature • **Effort:** L • **Deps:** S-44.4, S-14.9 • **FR/AD:** fnd:CAP-2 • fnd:AD-2, fnd:AD-5, fnd:AD-12, fnd:AD-13 (cell stays for 44.6), fnd:AD-15, fnd:AD-18, fnd:AD-19
**Given** the manifest rows for `.claude/skills/**`, `_bmad/**`, `_bmad-output/projects/**`, `docs/dreams/**`, `presentations/**` **When** the move lands **Then** estate-authored skills — the eight station personas included — live under `skills/{stations,personas,domain}/` with SKF export writing there, no adapter is tracked (the 44.11 link step generates `.claude/skills/<x>` on every machine and `.cursor/skills/<x>` where Cursor is detected), installer-written `bmad-*` / `skf-*` dirs are untouched, the CFE cell is left in place for 44.6 (`fnd:AD-13`), and the BMAD chain resolves in foundry with the marker and planning links generated, never copied; the move is `steward cutover apply --phase 1b`, replayable until the flip
**And** the flag flip that follows this story is an attended operator act with no loop running: `pyforge.cutover_root` → `foundry`, the eight loop homes re-provisioned against the foundry remote, the Realization log stamped (`fnd:AD-17`)
**And** the open question `planning-history-scope` is answered before dispatch
**And** this story refuses to run while `cutover-readiness.md` P11 or P12 reads anything but green (fnd:AD-10's own worked example) — after marshal 30.5 and 30.2 and steward 14.9, all confirmed `done` as of 2026-09-07; the check itself, not this prose, is what 44.5 runs against P11/P12's live state at execution time
**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch as a tree copy. Suite/skills appear by re-provision from the register (Epic 54 + later). Ledger stays `backlog`. Flag flip remains attended and after the kernel is verified, not after this file-move.
**Status:** backlog

### Story 44.6: CFE comes home

As a platform operator,
I want the authoritative conda-forge-expert skill, scripts and tools resolving from `skills/domain/conda-forge-expert` in foundry with Mason reaching the island by manifest path,
So that no `MASON_CFE_ROOT` resolves to `local-recipes` and retros land in the lasting repo.

**Type:** feature • **Effort:** M • **Deps:** S-44.5 • **FR/AD:** fnd:CAP-3 • fnd:AD-4, fnd:AD-5, fnd:AD-13, fnd:AD-16 • CLAUDE.md Rule 1 / Rule 2 (Mason)
**Given** `pyforge/mason/resolve.py`'s chain (flag → `MASON_CFE_ROOT` → cwd walk) **When** it runs in a foundry checkout **Then** the whole CFE cell (skill, `scripts/`, `tools/conda_forge_server.py`, the 76 `pixi.toml` references) lives under `skills/domain/conda-forge-expert/`, `_CFE_MARKER` and both detectors' path literals are rewritten, `MASON_CFE_ROOT` resolves there as a repo root, recipe build / submit / update are `pixi run --manifest-path factory/pixi.toml` subprocesses, and `mason-cfe-surface-check` + `cfe-rebuild-guard-check` pass **with the foundry epoch as their range floor** (a zero-commit range is exit 2, never clean)
**And** the story invokes `conda-forge-expert` and closes with a Rule-2 CFE retro
**And** — reciprocal note, not a `Deps:` token: **mason Story 15.1 (close the CFE rebuild campaign; delete-on-cutover) must land BEFORE this story moves the CFE cell to `skills/domain/`.** The rebuild Spec's surface and slice map are written against `.claude/skills/conda-forge-expert/**`; moving the cell first leaves that Spec pointing at a path that no longer exists and makes this story intractable (fleet readiness 2026-09-09, mason-E2 / § 2.3 C2)
**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch as a cell move. Foundry CFE is rebuilt from Specs; local-recipes is the oracle. Ledger stays `backlog`.
**Status:** backlog

### Story 44.7: The factory island

As a platform operator,
I want `factory/` with its own `pixi.toml` and lock, the recipe tooling, and a recipes-only CI,
So that recipe churn never re-solves the estate and `mason recipe build factory/recipes/<r>` matches today's CFE wrap.

**Type:** feature • **Effort:** L • **Deps:** S-44.3 • **FR/AD:** fnd:CAP-4 • fnd:AD-3, fnd:AD-4, fnd:AD-8 • R-17b • `DW-RT-2026-09-02-1`
**Given** `factory/pixi.toml` + `factory/pixi.lock`, `factory/recipes/`, `build-locally.py`, `.ci_support/`, `conda-forge.yml` **When** `mason recipe build factory/recipes/<r>` runs **Then** it matches today's CFE wrap, the estate lock carries no solver-farm dependency, and island CI triggers on `paths: factory/**` only
**And** `DW-RT-2026-09-02-1` is resolved
**And** — reciprocal note, not a `Deps:` token: **`spec-reusable-cicd-workflows`' trigger ("a SECOND consuming repo") fires here.** Consult that extension-point at 44.7 rather than re-deriving the island's CI shape from scratch (fleet readiness 2026-09-09, mason-E3 / Class D D11)
**Status:** done

### Story 44.8: The working set

As a platform operator,
I want only in-flight and sole-maintainer recipes in `factory/recipes/`,
So that the 7,855-directory universe is never copied.

**Type:** feature • **Effort:** M • **Deps:** S-44.7 • **FR/AD:** fnd:CAP-5 • fnd:AD-2, fnd:AD-10
**Given** manifest rows with `reason ∈ {in-flight, sole-maintainer, referenced-by-spec}` **When** the recipes move **Then** `factory/recipes/` is exactly that set and island CI asserts `count <= manifest rows`
**And** every other `recipes/**` row reads `stays` (archived with `local-recipes`)
**And** — reciprocal note, not a `Deps:` token: **`spec-fleet-stewardship` CAP-1's `recipes/**` surface is mostly archived after this story**; its Dream and Spec carry a dated dormancy note (mason, 2026-09-09) so the surface is not read later as live (fleet readiness 2026-09-09, mason-E4 / Class D D11)

### Story 44.9: Mason submits to conda-forge

As a platform operator,
I want `submit` targeting staged-recipes or the bot fork and `update` targeting the feedstock maintainer-edit path from foundry,
So that an agent-opened PR never targets `local-recipes`.

**Type:** feature • **Effort:** M • **Deps:** S-44.6, S-44.8 • **FR/AD:** fnd:CAP-6 • fnd:AD-4, fnd:AD-9, fnd:AD-11 • CLAUDE.md Rule 1 / Rule 2 (Mason)
**Outward (`fnd:AD-9`):** opens pull requests against conda-forge — held `blocked`; dispatched only on the operator's explicit confirmation.
**Given** the submit path **When** an agent submits **Then** the target is staged-recipes or the bot fork, never `local-recipes` (asserted in a test on the submit path), and feedstock updates use the maintainer-edit path

### Story 44.10: Archive local-recipes

As a platform operator,
I want `local-recipes` read-only with its README superseded, Azure disabled, the last SHA pinned in foundry, history kept, and the worktree residue retired,
So that the default clone is foundry and `.steward` has one git root.

**Type:** feature • **Effort:** M • **Deps:** S-44.1, S-44.2, S-44.3, S-44.4, S-44.5, S-44.6, S-44.7, S-44.8, S-44.9 • **FR/AD:** fnd:CAP-7 • fnd:AD-1, fnd:AD-8, fnd:AD-9, fnd:AD-11 • `DW-CC-2026-09-04-1`
**Outward, irreversible (`fnd:AD-9`):** disables CI and archives a repository — held `blocked`; dispatched only on the operator's explicit confirmation.
**Given** every other 44.x `done` **When** the archive lands **Then** the README opens with the supersession banner, Azure pipelines are disabled, the final SHA is pinned in the foundry manifest and the Dream's Realization log, history is kept, the 268 registered worktrees are retired, and a fresh clone of foundry is the default working tree
**And** `DW-CC-2026-09-04-1` is resolved

### Story 44.11: Windows-native estate

As a developer on a stock Windows machine with no WSL and no Developer Mode,
I want the estate to clone and run natively — links generated as junctions, paths under the limit, no shell-only tasks — with the host reached remotely,
So that the Windows population does recipe, station and planning work first-class.

**Type:** feature • **Effort:** L • **Deps:** S-44.3 • **FR/AD:** fnd:CAP-1, fnd:CAP-2, fnd:CAP-3 • fnd:AD-5, fnd:AD-19
**Given** a fresh clone on Windows with `core.symlinks` off **When** the link step runs **Then** every runtime link (`.claude/skills/<x>`, the two BMAD planning links, `.cursor/skills/<x>` where Cursor is detected) exists as a junction, none is tracked in git, and a doctor preflight reports them healthy
**And** the preflight fails loud on a link that is a text file and on the deepest tracked path exceeding the Windows limit from the clone root; long-path registry settings are never assumed
**And** no pixi task invokes `bash -c`, `sed`, `grep`, `awk`, `find` or `tee` (audited in a test); runtime state resolves to gitignored `var/`
**And** a win-64 CI leg runs the station suites, the link check and the detectors green; the remote-dev profile for the host is documented in the bootstrap Spec

### Story 44.12: Cutover flag and replay harness

As a platform operator,
I want one flag that names the root of record and a harness that regenerates, appends and replays the cutover plan,
So that `local-recipes` keeps evolving until the flip and foundry never falls behind it.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-8 • fnd:AD-2, fnd:AD-17, fnd:AD-18 • canopy:AD-11
**Given** `src/platform/config/flags.json` **When** `pyforge.cutover_root` is read **Then** the host reads it in-process and the CLIs read it through a `pyforge-core` reader; its value alone decides the ledger of record, Mason's targets and the loop-home remotes, and flipping it back restores them
**And** `steward cutover plan --regenerate` and `--append` both preserve `moved` rows (a test proves idempotence over status), and `steward cutover apply --phase <n>` is idempotent when re-run
**And** a flip is refused while any loop is running and is recorded in the Dream's Realization log
**Status:** done

### Story 44.13: Memlog fidelity

As a platform operator,
I want every hand-edit in a rendered `SPEC.md` folded back into its memlog and every Spec proven to re-render without loss,
So that Dreams plus memlogs can seed foundry and nothing decided is lost in the re-derivation.

**Type:** docs • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-2 (prerequisite), fnd:CAP-9 • fnd:AD-20
**Given** every `specs/spec-*/SPEC.md` across the eight stations **When** `bmad-spec` re-derives it from its memlog into a scratch folder **Then** the result is byte-equivalent to the rendered file, or every difference is recorded as a memlog entry and the re-derive is repeated until equivalent
**And** the unifying strategy Spec, hand-edited past its memlog today, is reconciled first and its "never re-derive" exception is retired
**And** this runs in `local-recipes` before Phase 0; a Spec that cannot be made to re-render without loss is a review-blocking finding, not a silent carry
**And** every spine's own `.memlog.md` re-distills through `bmad-architecture` without loss (closing G6 — 44.13's own scope previously only exercised one re-derive, 44.14's)

### Story 44.14: Rebuild harness and oracle gate

As a platform operator,
I want a rebuild path in foundry — Dream and memlog to re-derived Spec, spine and epics, drained by Marshal — that cannot pass without the archived suite passing against it,
So that a rebuilt capability is a regeneration drill, never a rewrite by another name.

**Type:** feature • **Effort:** L • **Deps:** S-44.12, S-44.15 • **FR/AD:** fnd:CAP-9 • fnd:AD-18, fnd:AD-21, fnd:AD-22, fnd:AD-23 • regenerable-factory Dream (the drill)
**Given** one pilot capability marked `rebuild` (Scribe, per the first pass) **When** the harness runs in foundry **Then** its Spec, spine and epics are re-derived from the moved memlog, Marshal drains its stories under the metered `steward budget` ceiling (44.15), and the archived Scribe suite passes against the rebuilt code before the row reads `verified-in-foundry`
**And** the moment the row entered `rebuilding` its source paths froze in `local-recipes`, and `steward cutover plan --append` reports any change against them as a finding
**And** the harness is reusable for every later `rebuild` row without operator scripting

### Story 44.15: Actions-minutes metering

As a platform operator,
I want `steward budget check` to meter the account's GitHub Actions minutes against the plan's included minutes and my declared ceiling,
So that the foundry dispatch, Marshal's drains and the rebuild harness read a real budget instead of discovering the ceiling by being refused.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-10 • fnd:AD-14, fnd:AD-23 • steward Epic 4 (4.1–4.3, the honest stub) • `feedback_gh_actions_api_gotchas`
**Given** a `user`-scoped GitHub credential held in `steward keys` (never in the manifest or `.steward/budget.yaml`) and a ceiling declared by `steward budget set` **When** `steward budget check` runs **Then** it reads the account's Actions billing API, reports included, used and remaining minutes with the private-repo multipliers applied, and returns a real under/over verdict — `EXIT_BUDGET_NOT_CONFIGURED` only when no metering source is configured
**And** the meta invariant `test_no_cost_integration_sdk_imported_in_budget` is amended for this one source (the GitHub billing API; still no cloud-cost SDK), and every other spend source keeps reporting the honest stub
**And** `steward budget check --json` is consumable by the 44.3 confirmation, by Marshal's foundry drains and by the 44.14 harness as their ceiling, and a refused runner ("payments have failed" / spending limit) is reported as a finding, never as a cheap green

## Currency validation note — 2026-08-26

Chain-currency sweep pass (arch→epics cascade safety, no story or status changes).
Validated this breakdown against the same-day reconciliations of the station brief, PRD,
and `architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`, plus the Canopy
spine (`architecture-pyforge-unifying-strategy-2026-08-24`) already listed in
`inputDocuments`: every `### Story` heading still maps 1:1 to a
`sprint-status-ledger.yaml` key (marshal:AD-72 holds; 37 epics / 131 stories, all `done` per the
ledger as of this date), the Epic 18–37 chain sections match the strategy SPEC's
CAP-1..145 state (`open_questions: []` since 2026-08-26; CAP-19's first slice = Epics 34
and 36 here; Epic 35 correctly attributed to `spec-mcp-era-isolation` CAP-4, not the
unifying CAP set), and the AD-4 amendment (Story 30.2's `dashboard-gen` retirement) is
already reflected by Epic 30's own text. No epic or story required correction.

**2026-09-04 addendum (foundry cutover, solutioning iteration 4):** 44 epics / 168 `### Story` headings (this file; the 2026-09-04 iteration-3 figure of 210 was not reproduced). Epic 44's stories are `blocked` by design until the operator flips each — 44.13 flipped to `backlog` 2026-09-04 (the first flip; Phase 4 opens), the other fourteen `blocked` (solutioning under operator review, `fnd:AD-9`); the 2026-08-26 count above is historical.

## Epic 45: eval-quality joins the suite and the reviewer gets measured (spec-bmad-eval-quality CAP-1 CAP-2)

`eval-quality` (bmad-code-org) becomes a `bmad-suite` member the suite's way, and one Behavioral Evaluation Contract proves — with a planted `file:line` defect and a catch rate — that the review layer bmad-loop relies on actually looks. Dream: `docs/dreams/bmad-eval-quality.md`; Spec: `spec-bmad-eval-quality` (`packaging.md`, `pilot-contract.md`). Story 45.2 is `blocked` until the operator flips it: every trial spends Claude budget (`--max-budget-usd`), and the pilot is a measurement of the reviewer, never a PR gate.

### Story 45.1: eval-quality joins the suite

As a fleet operator,
I want `bmad-eval-quality` packaged, enrolled and pinned like every other suite member,
So that every consumer of the suite gets the 0.2.0-line binary that has `score`, and the fourteenth member costs one manifest line, not a parallel list.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** spec-bmad-eval-quality CAP-1 • `packaging.md` • CFE Rule 1 + Rule 2 • overrides spec-bmad-suite-channel-product § Non-goals for this one member (operator 2026-09-05)
**Given** `recipes/bmad-eval-quality/recipe.yaml` commit-pinned `0.2.0.dev0 @ 3172162fbdc7c4bb70ed11c1367dc3e433797535` (sha256 `a8b1ddfb…`), built through `conda-forge-expert` in the `bmad-method` npm-CLI class **When** `recipe-build` runs **Then** it is green and `eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `compile` on a shipped corpus contract exits 0
**And** enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml`; `generate-bmad-suite` regenerates the metapackage run deps and CalVer (the same pass retires `bmad-method-wds-expansion` — deprecated in the 6.12.0 core module registry, absorbed by `bmad-ux` — so the suite stays at 13 active members)
**And** `pixi.toml` pins `bmad-eval-quality = ">=0.2.0.dev0"`, `environment.yaml` is regenerated, `tests/packaging/test_bmad_suite_full_feature.py`'s baseline set, steward's `suite.py` `SuitePackageDef` + pipeline-truth fixture, `install-matrix.md`, `install-class-playbook.md` and `library-llms-full.md` each carry the member; `llms-full-check` is green; the PR carries `maintenance`
**And** publishing to SelfExplainML (`anaconda upload`) is the operator's step and is not claimed by this story

### Story 45.2: The reviewer is measured against a planted defect

As a fleet operator,
I want one twin-run contract that runs the `edge-case-hunter` review layer against a clean diff and a diff with one planted boundary flip at `pkg/discount.py:17`,
So that the last line of defence under `gate_mode = "none"` has a catch rate the fleet can read instead of a feeling.

**Type:** feature • **Effort:** L • **Deps:** S-45.1 • **FR/AD:** spec-bmad-eval-quality CAP-2 • `pilot-contract.md` • operator flip required (`blocked`)
**Given** `evals/review-catches-planted-defect/` with the fixture package, `arms/clean.diff`, `arms/mutated.diff`, the contract (interface `review-api`, operation `review-diff`, kind `api`, 21 required fields modelled on `corpus/dev/contracts/satisfied-declarations.json`), probes, scoring policy, isolation manifest, evaluator configuration and a findings JSON schema **When** `eval-quality-smoke` runs **Then** the shipped corpus compiles and the pilot contract compiles
**And** the ~150-line `subprocess`-only driver runs the layer headlessly (`claude -p --output-format json --json-schema … --max-budget-usd 2 --no-session-persistence`, model pinned to the station's `[adapter.review].model`), maps exit code + parsed findings to an observation and emits the sealed run record; the one strong oracle is `covers-by-key` over `referenceSets.planted-defects` (`["file","line"]`) — "the review ran" never passes alone
**And** a one-trial `eval-quality-review-twin-run` preflights both arms; the mutated arm's review cites `pkg/discount.py:17` and the clean arm does not; `-- --trials 3` yields a policy-comparable strength vector with a catch rate; `eval-quality-review-replay` replays a sealed record
**And** none of the three pixi tasks joins `detectors` / `detectors-ci`; Warden stays the sole PR verdict

## Epic 46: The bmad-suite is wielded by the fleet (spec-bmad-suite-lifecycle CAP-1..145)

**Spec binding.** Decomposes `spec-bmad-suite-lifecycle` CAP-1..145 (Spec landed 2026-09-06 from
`docs/dreams/bmad-suite-lifecycle.md`; companions `adoption-register.md`, `release-cadence.md`;
PRD `prd-bmad-suite-lifecycle-2026-09-06` suite:FR-1..suite:FR-8; spine
`architecture-bmad-suite-lifecycle-2026-09-06` AD-1..AD-7). Operator decisions 2026-09-06: adopt
utility-skills, manticore (Herald), labs skill-by-skill, the eval-quality pilot; BMB beside skf;
TEA full adoption. **HARD boundaries:** provision by install class only — no hand copies, never
`cleanup-legacy.py`, never `bmad-module-skill-forge uninstall` (AD-1); one wielding station per
skill, routing in the persona skill + AGENTS block, never CLAUDE.md (AD-2); advisory lenses never
gate (AD-4); a repo mechanism is deleted only behind a recorded equivalence check (AD-5); kin
chains keep their mechanisms — this epic relays, never absorbs (AD-7). Station-side halves are
their own stories (marshal 31.x, doctor 20.x, warden 11.x, herald 18.x, scribe 7.1, atlas 24.1,
mason 14.1) and are named in each story's acceptance, never restated here.

### Story 46.1: The adoption register governs wiring
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-1 • AD-6 • PRD suite:FR-1
**Surface:** `specs/spec-bmad-suite-lifecycle/adoption-register.md`, memlogs of `spec-bmad-suite-channel-product` / `spec-bmad-611-era-alignment`, `bmad-agent-steward` skill (routing-note home decision)
**Given** the thirteen-row register **When** any member's verdict, wielder or provisioning path changes **Then** the row changes first and `steward suite pipeline-truth`'s `wired` column agrees with the register for 13/13 (disagreement is a finding on the register)
**And** the channel-product "never wire-everything" constraint and the one-front-door row-6 triage are recorded as superseded/closed by memlog (landed 2026-09-06 in the planning PR); this story verifies — not decides — the spine's settled calls: routing home = the persona skill with one AGENTS pointer line (AD-2), studio root = `$PYFORGE_STUDIO_ROOT` defaulting to `~/pyforge-studio/` (AD-3), provisioned-module roster = `_bmad/custom/config.toml [modules.<code>]` (AD-9)
**And** it ships the AD-2 meta-test: every register § 2 skill dir is named by exactly one `bmad-agent-<station>` persona skill and by CLAUDE.md never; the register's status cells hold story keys only (AD-6)

### Story 46.2: utility-skills is provisioned and its ten skills have wielders
**Type:** feature • **Effort:** S • **Deps:** S-46.1 • **FR/AD:** suite:CAP-2, suite:CAP-3 • AD-1, AD-2 • PRD suite:FR-2/suite:FR-3
**Surface:** `steward provision --module utility-skills` (existing backend), `.claude/skills/bmad-os-*`, `_bmad/config.yaml` manifest section, `bmad-agent-steward` (routes `bmad-os-skill-to-bundle`)
**Given** `bmad-utility-skills` 2.0.0 in the pixi env **When** `steward provision --module utility-skills --json` runs **Then** ten `bmad-os-*` dirs land, `--list-modules` reports the module installed, the retired-ID guard and integrity meta-tests stay green, and `DW-FU-15-3-4` (the `_CIS_SKILL_NAMES`-style allowlist unasserted) gains a live-tree assertion for this module
**And** provision's roster writer moves from `_bmad/config.yaml` (a file 6.12 does not ship) to `_bmad/custom/config.toml [modules.utility-skills]` carrying `provisioned_by`, `installer`, `skills` and the module's `module.yaml` answers at the installer's key paths (AD-9); `--list-modules` reads that roster; the suite:CAP-8 pre-flight scan compares conda-module skills against `share/bmad-utility-skills/skills` (AD-9)
**And** the register § 2 rows for the ten skills carry their story keys: herald 18.2 (`changelog`, `changelog-social`), doctor 20.4 (`root-cause-analysis`), warden 11.1 (`review-pr`, `findings-triage`), scribe 7.1 (`diataxis`, `audit-file-refs`, `editorial-review-translation`), marshal 31.6 (`gh-triage`), steward (`skill-to-bundle`, this story)

### Story 46.3: TEA is provisioned and `tea-test-review` is a pixi task
**Type:** feature • **Effort:** S • **Deps:** S-46.1 • **FR/AD:** suite:CAP-2, suite:CAP-4 • AD-1, AD-4 • PRD suite:FR-4
**Surface:** `steward provision --module tea` (existing backend), `.claude/skills/bmad-testarch-*`, `pixi.toml` (one task `tea-test-review`, feature `local-recipes`), `environment.yaml`
**Given** TEA 1.24.0 in the pixi env **When** `steward provision --module tea --json` runs **Then** the nine `bmad-testarch-*` workflows and the Murat agent land, the AD-9 roster gains `[modules.tea]` with TEA's `module.yaml` answers — `test_artifacts` (84 references) pointed at each station's `planning-artifacts/` per its `.bmad-config.toml` — so `render_skill.py` renders `bmad-testarch-test-design` on the first try (the acceptance test), `--list-modules` reports TEA installed, and a pixi task `tea-test-review` wraps `tea-test-review --base origin/main --min-score <N>` taking `N` as an argument (default 80; marshal 31.3 supplies the calibrated value — AD-4 argument/value split)
**And** the task is NOT a member of `detectors` / `detectors-ci`; Warden's gate exit code is unchanged by it (AD-4); the six blanket-glob specs governing `pixi.toml` each get a memlog line and a scoped `spec_surface_check.py --write-baseline --spec`
**And** the marshal-side migration (31.1–31.3) and the warden advisory (11.2) depend on this story, not the reverse

### Story 46.4: bmad-builder is provisioned beside skf, with the cleanup-legacy guard proven
**Type:** feature • **Effort:** S • **Deps:** S-46.1 • **FR/AD:** suite:CAP-2 • AD-1 • PRD suite:FR-2 • addendum § Rejected alternatives
**Surface:** `steward provision --module bmb` (existing `SetupSkillBackend`), `.claude/skills/bmad-bmb-setup` + the four builder skills, `provision.py`, `tests/unit/test_provision*.py`, `bmad-agent-steward` (routing)
**Given** `bmad-builder` 2.2.2 in the pixi env and the existing `SetupSkillBackend` (which drives `bmad-bmb-setup`'s config merge but copies no skills — adversarial review F-5) **When** `steward provision --module bmb --json` runs with the backend extended to copy `share/bmad-builder/skills/*` **Then** `bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner` land, the wire-time skill-name collision check passes against the sixteen `skf-*` dirs, and `_bmad/config.yaml` gains the `bmb` section
**And** a unit test proves the backend never passes `--legacy-dir` and never invokes `cleanup-legacy.py` (it would `rmtree` this repo's `_bmad/core/config.yaml`), so the hazard is held by a test, not a comment
**And** `bmad-agent-steward` routes persona/workflow authoring to the builder skills and domain-skill compilation to `skf-*` — two pipelines, one register row each

### Story 46.5: labs-skills arrive by name and by consent
**Type:** feature • **Effort:** S • **Deps:** S-46.1 • **FR/AD:** suite:CAP-6 • AD-1, AD-6 • PRD suite:FR-6
**Surface:** `steward provision --plugin labs --skill <name>` (new: the one wrapped writer for the plugin-path class, AD-1 — copies the named skill from the conda member's share tree pinned to the recipe's commit, or calls `npx skills add` pinned to that commit; never both), `.claude/skills/{mcp-builder,slides-generator,multi-repo-git-ops,release-please}`, the AD-9 roster (`[modules.labs]` listing each installed skill), `adoption-register.md` § 2, `bmad-agent-steward` (routes `release-please`), one meta-test asserting no other labs skill is present
**Given** the operator's consent list of 2026-09-06 (exactly four skills) **When** each is installed by name through the wrapper **Then** the four dirs exist, the register's provisioning-path cell equals the wrapper invocation, each has a register row naming its wielder (atlas 24.1, herald 18.3, marshal 31.6, steward), and a meta-test reds any additional `bmad-labs` skill dir
**And** the install-class playbook row for `bmad-labs-skills` records the consent list and the by-name command as the documented native path

### Story 46.6: Herald's manticore studio has a root and a proven native path
**Type:** feature • **Effort:** M • **Deps:** S-46.1 • **FR/AD:** suite:CAP-5 • AD-3 • PRD suite:FR-5 • Spec open question 1 (studio root)
**Surface:** `install-class-playbook.md` (manticore row → studio path), `.gitignore` (studio artifacts if in-repo), `adoption-register.md` row 9 (studio path cell), a steward doc `docs/reference/manticore-studio.md` (or the playbook section) with the exact `--custom-source` procedure
**Given** the studio root declared once per machine by `PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio/`, AD-3 — the register cell and herald's CLI cite it, never restate it) **When** the native path `npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-manticore` is run once in that root with `mc-setup` writing `[modules.manticore]` into the studio's own `_bmad/custom/config.toml` **Then** the fifteen `mc-*` skills exist in the studio, this repo's `_bmad/` and `_bmad-output/` are byte-identical before and after (a checksum recorded in the story), and the register row carries the root
**And** the prerequisites (uv, ffmpeg, node, git) are asserted by a `steward provision --module manticore --dry-run`-style check or documented as the studio's own check; Herald's first render is herald 18.1, not this story
**And** the stale `[modules.manticore]` block in the gitignored `_bmad/custom/config.user.toml` is removed; pipeline-truth's manticore probe reads the declaration and the studio's `mc-*` census (AD-6); a `--studio <dir>` flag on `steward provision --module manticore` is minted only if this native path proves clumsy (spine Deferred)

### Story 46.7: skf is pinned to `v2.1.0` and suite:CAP-7 is exercised live
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** spec-bmad-method-core-upgrade CAP-7 (+ answered Q3/Q5) • spec-bmad-suite-lifecycle CAP-2
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml` (`custom_modules[skf].pin`), `tests/unit/test_upgrade_apply.py` (pin argv), core-upgrade memlog
**Given** the 2026-09-06 verification (npm 2.1.0 tarball `src/` == GitHub tag `v2.1.0`, 337 files, `diff -rq` empty) **When** the catalog's `custom_modules` entry for skf reads `pin: v2.1.0` **Then** the apply argv carries `--pin skf=v2.1.0`, the unit test asserts it, and the next live apply (Session 2 step 9, the `--no-shims` retirement) exercises suite:CAP-7's restore → own-installer → verify path against the pinned source
**And** skf stays registered as a bmad-method custom module (`bmad-help` routing for fifteen skills); the install-class playbook row is unchanged (own-installer)
**Status:** done
**Outcome (2026-09-06):** catalog pin flipped `null` -> `v2.1.0`; `test_real_catalog_pins_skf_v2_1_0`
added (loads the real catalog, not a fixture). Session 2 step 9's live `--no-shims` apply the
same day exercised suite:CAP-7 for real: skf own installer exit 0, 16/16 skill dirs verified, config
restored.

### Story 46.8: CIS is re-provisioned to the packaged revision
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** suite:CAP-2 • AD-1 • customization-inventory C11
**Surface:** `.claude/skills/bmad-cis-*/SKILL.md` (10 files), `steward provision --module cis` (idempotent re-provision)
**Given** the packaged `bmad-creative-intelligence-suite` 0.3.2 passes `--project-root {project-root}` on every `resolve_customization` call and the installed copies do not (15 lines across 10 files) **When** `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --module cis --json` runs **Then** `git diff --stat -- '.claude/skills/bmad-cis-*'` shows exactly those 10 files / 15 lines, nothing else moves, and the retired-ID guard stays green
**And** atlas `DW-FU-20-4-3` (the `{{project_name}}` placeholder in `bmad-cis-design-thinking/template.md`) is re-checked against the refreshed copy and closed or re-verified in the atlas ledger
**Status:** done
**Outcome (2026-09-06):** re-provisioned exactly the 10 files / 15 lines; retired-ID guard
stayed green. `DW-FU-20-4-3` re-verified still genuinely open (unrelated upstream placeholder
bug), recorded with dated evidence in the atlas ledger.

### Story 46.9: pipeline-truth's installed stage reads the applied core, and `wired` is a declared per-class predicate
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-channel-product CAP-1 (relayed hole #1, 2026-09-05) • spec-bmad-suite-lifecycle CAP-8
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` (installer-tree class `installed` probe), `tests/unit/test_suite*.py`, `install-matrix.md` (installed-stage caveat retired)
**Given** the installer-tree member `bmad-method` **When** pipeline-truth computes its `installed` value **Then** it reads `_bmad/_config/manifest.yaml` `installation.version` (the applied core), falls back to the pixi env's conda-meta only when the manifest is absent, and reports both when they differ (`applied 6.11.0 / env 6.12.0`) as a named drift
**And** the fixture that replays 2026-09-05's false green (env 6.12.0 while `_bmad/` was 6.11.0) now fires the drift; doctor's core-drift check stays the loud signal and is not duplicated
**And** each `SUITE_PACKAGES` row carries the expected `wired` probe value for verdict `wield` in its class, each class probe observes the provisioning path the register names (labs: the named skill dirs and no other; manticore: the AD-3 declaration + `mc-*` census; bmb: the five dirs; module class: the AD-9 roster), and the register's `Wired` column is regenerated from `pipeline-truth --json` (AD-6)

### Story 46.10: The release cadence is one verified runbook
**Type:** chore • **Effort:** S • **Deps:** S-14.10 • **FR/AD:** suite:CAP-8 • AD-7 • PRD suite:FR-8
**Surface:** `specs/spec-bmad-suite-lifecycle/release-cadence.md` (verified against the 14.9 apply and the 14.10 rehearsal)
**Given** `release-cadence.md` and the two live passes core-upgrade owns (the `--no-shims` apply, 14.9; the `@next` rehearsal, 14.10) **When** each of the nine runbook steps is annotated with the command that actually ran, its exit, and its owner **Then** no step reads "improvised"; the `@next` rehearsal recipe in the runbook matches 14.10's recorded invocation verbatim; the runbook never claims the rehearsal as the live proof that flips `spec-bmad-method-core-upgrade` to `shipped` (AD-7: the mechanism and its findings live in core-upgrade's chain)

## Epic 47: The BMAD estate is cutover-ready (spec-bmad-suite-lifecycle CAP-9)

**Spec binding.** Decomposes `spec-bmad-suite-lifecycle` CAP-9 (companion `cutover-readiness.md`:
prerequisites P1–P17, gaps G1–G11; PRD FR-9; spine AD-7, AD-8 and the inherited `fnd:AD-5`,
`fnd:AD-12`, `fnd:AD-20`). **HARD boundaries:** the cutover Spec is evergreen and never re-derived —
this epic writes memlog relays and readiness artifacts, never Epic 44 stories; Story 44.3 is not
flipped while any P line is red (AD-8); the mechanisms stay with their owners (14.8 re-applies
customizations, marshal 30.2/30.5 retire rulebooks and shims, doctor 20.2/20.3 build the
detectors) — this epic proves and relays (AD-7).

### Story 47.1: The readiness checklist is live and the pre-flight is its P7 signal
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** suite:CAP-9 • AD-8 • PRD FR-9
**Surface:** `specs/spec-bmad-suite-lifecycle/cutover-readiness.md` (state column), `steward upgrade bmad-core` pre-flight (report-only run, recorded), `docs/dreams/bmad-suite-lifecycle.md` § Realization log
**Given** P1–P17 with owners **When** this story runs the report-only pre-flight (`--target 6.12.0 --package-root <cached 6.12.0> --installed-package-root <cached 6.12.0>`) **Then** the local-customization findings are the P7 evidence (seven files today), each is checked against a spec `surface:` (P13 — marshal 31.4 governs the five ungoverned ones), and the checklist's state column is refreshed with a dated pass
**And** the checklist names the exact re-run command so every later pass is mechanical; a P line turning green is a memlog `(event)` on this Spec

### Story 47.2: `skf-export` is proven to accept the foundry skills root
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** suite:CAP-9 (G5, P10) • `fnd:AD-5`
**Surface:** `_bmad/skf/config.yaml` (`skills_output_folder`, `snippet_skill_root_override` — exercised in a scratch copy, never edited in place), a scratch worktree, `cutover-readiness.md` G5/P10
**Given** the cutover spine's claim that SKF export writes to `skills/stations/<x>/` **When** `skf-export-skill` runs in a scratch worktree with `skills_output_folder: skills/stations` **Then** the export lands there with a working adapter under `.claude/skills/<x>` generated by the link step's shape, or the story records precisely which key/option skf lacks — a finding for `spec-python-foundry-cutover` by memlog, never a silent assumption
**And** P10's "hand-set keys survive an apply" half is re-verified against suite:CAP-7's restore on the same run, and the story records the single declaring key (`_bmad/custom/config.toml [modules.skf].skills_output_folder`, fnd:AD-12) from which `_bmad/skf/config.yaml` is re-rendered — never restored from git

### Story 47.3: `_bmad/**` joins Epic 44's surface and `PROJECTS.md` carries the cutover layout
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** suite:CAP-9 (G1, G8) • `fnd:AD-12`
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml` (`[epic_surfaces] "44"`), `_bmad-output/PROJECTS.md` (§ config layers, § Adding a new project), cutover memlog
**Given** fnd:AD-12 moves `_bmad/` in Story 44.5 but `[epic_surfaces] "44"` omits `_bmad/**` (MRS-GATE-007 would fire) **When** the glob is added and `PROJECTS.md` gains a "cutover target" subsection (marker + planning links generated per machine — symlink on POSIX, junction on Windows — never copied; `bmad-switch` semantics unchanged until the flip) **Then** `marshal factory drain` accepts a 44.5-shaped change and the two PROJECTS.md sections cited by `cutover-readiness.md` G8 no longer contradict `fnd:AD-12` / `fnd:AD-19`

### Story 47.4: The foundry stack carries a `bmad-*` floor row
**Type:** docs • **Effort:** XS • **Deps:** — • **FR/AD:** suite:CAP-9 (G9) • AD-8
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` § Stack (via `bmad-architecture` update from its memlog — the `(decision)` landed 2026-09-06), `cutover-readiness.md` G9
**Given** the spine memlog decision of 2026-09-06 **When** `bmad-architecture` update re-distills the cutover spine **Then** § Stack gains one row: `bmad-method >=6.12.0, bmad-loop >=0.11.1, bmad-module-skill-forge >=2.1.0 (linux-64 only), bmad-creative-intelligence-suite, bmad-method-test-architecture-enterprise, bmad-eval-quality, bmad-utility-skills, bmad-builder` with the note that win-64 (44.11) excludes skf and eval-quality; AD ids unchanged

### Story 47.5: Epic 44 depends on the era tail, and 44.13's scope names the spines
**Type:** docs • **Effort:** XS • **Deps:** S-14.9 (after marshal 30.5 and 30.2 — cross-station: ledger `blocked`, fnd:AD-10) • **FR/AD:** suite:CAP-9 (G2, G3, G6) • AD-7
**Surface:** `epics.md` Epic 44 stories 44.5 / 44.12 / 44.13 (`Deps:` lines only), cutover memlog, `sprint-status-ledger.yaml` (via generate + sync)
**Given** the shim retirement (14.9, 30.5) and the rulebook retirement (30.2) are prerequisites the cutover text assumes **When** 44.5 gains `Deps: …, S-14.9` with the trailing prose "after marshal 30.5 and 30.2" plus a `blocked` ledger row and an in-story check (fnd:AD-10 — never a foreign-station token), and 44.13's acceptance gains "and every spine `.memlog.md` re-distills through `bmad-architecture` without loss" (recorded first as a cutover memlog `(note)`) **Then** `forward-dependency-check` reads the new edges, `cutover-readiness.md` G2/G3/G6 read relayed-and-landed, and no Epic 44 story text beyond `Deps:` and that one acceptance clause changes


## Epic 48: The chain tells the truth (spec-pyforge-unifying-strategy Residual 2026-09-09)

**Spec binding.** Decomposes `spec-pyforge-unifying-strategy` § Residual (2026-09-09) and the
Constraints block *Correct-course 2026-09-09* — the syncer guards, the five open red-team
directives R-18..R-22 (`DW-RT-2026-09-02-2..6`), the CAP-axis namespace pass, and the Single-Spec
merge the Dream has named since 2026-09-01. Minted by
`sprint-change-proposal-2026-09-09-currency-review.md` from
`research/currency-review-pyforge-unifying-strategy-2026-09-09.md`. **HARD boundaries:** no shipped
epic reopened, no shipped CAP re-minted; Story 48.1 dispatches first and alone, and **no
`sprint-ledger-sync` of any form runs on this project until it lands** (the feed lagging the twin by
this epic's keys is correct); 48.8 never renames `[feature.python-agent-platform]`.

### Story 48.1: The ledger syncer guards blocked and missing keys
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** Spec Constraints (2026-09-09) • review § 0
**Surface:** `scripts/promote_sprint_status.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py` (marshal owns the test file, steward the fix — the amendment is named here, coordinated at dispatch), `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` (the `epic-44`…`epic-49` rollup rows), `AGENTS.md` § Running and verifying **and** `AGENTS.md:49`'s `--repair-feed` instruction (both via `bmad-project-context` refresh — managed block, never by hand), `docs/dreams/pyforge-unifying-strategy.md` § Cutover Order line
**Given** a tracked-twin row `blocked` and the same key `backlog` in the Tier-3 feed **When** any sync runs — bare or `--repair-feed` **Then** the twin's `blocked` survives (a `STICKY_STATUSES` set mirroring `sprint_plan.py:77`), and a key present in the twin but absent from the feed is restored or refused — never silently dropped — on the bare path too (`main()` today acts on `missing` only under `--repair-feed`)
**And** the fix is **station-agnostic by construction**: `STICKY_STATUSES` exists at `sprint_plan.py:77` and has **no syncer counterpart for ANY project** — steward is merely the station with 14 `blocked` rows to lose — so the success criterion may not be written against "the current feed" and "all 14 `blocked` rows" alone (fleet readiness 2026-09-09, stB-E4)
**And** the **epic-rollup defect** is fixed in the same story: steward's `epic-44`…`epic-49` all read `backlog` while their stories read `done` (`epic-45` with 45.1/45.2 both `done`; `epic-46` 9/10; `epic-47` 5/5) while `epic-38`…`epic-43` read `done` — rollup stopped happening around Epic 44, which makes `fleet-picture` understate steward. It is adjacent to the sticky-status gap but a **distinct defect**, and it is not steward-only: atlas `epic-24` and warden `epic-11` show the same shape (fleet readiness 2026-09-09, stA-D8)
**And** the regression test that pinned `TERMINAL == {"done"}` (`src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py:55`) is **amended** — it pins the bug — and rewritten to assert both guards with fail-without cases; `sprint-ledger-sync --project steward --repair-feed` run against the current feed leaves all 14 `blocked` rows intact; `AGENTS.md:49` is corrected through `bmad-project-context` (it still instructs every agent to run `sprint-ledger-sync … --repair-feed` before any ledger write, which the currency review withdrew)
**And** the one-line **`scratch-worktree-lifecycle` landing ritual** lands in the same managed-block refresh — `steward workspace start/status/clean` as the documented way to open a landing worktree, instead of the hand-run `git worktree add` every landing pass still uses; that is the whole adoption cost of a `done` Epic 13 half that has never been invoked (fleet readiness 2026-09-09, stB-B8)

### Story 48.2: R-18 sizing rewrite
**Type:** feat • **Effort:** M • **Deps:** — • **FR/AD:** `DW-RT-2026-09-02-2` • red-team S-7, T-7
**Surface:** `src/platform/deploy/charts/platform/values.yaml`, `templates/*-deployment.yaml`, a new `hpa.yaml` + `pdb.yaml`
**Given** the review's sizing findings **When** per-pod requests/limits land for web (memory-bound; `--preload`; Langflow RSS measured), worker (CPU-bound; separate builds pool), mcp-host, DB-GPT sidecar, Liquibase Job (JVM) and Vizro **Then** HPA exists on web and worker, PodDisruptionBudgets exist, LLM inference is stated external, and `helm template` renders the resources under the chart's existing invariant tests
**And** the **ASGI thread-pool size is set deliberately** rather than left at the framework default (`ANYIO_MAX_THREADS` or equivalent), justified against the same measured Langflow RSS this story already takes as input — closing the `spec-asgi-multiplexer-monolith` residue recorded at `spec-local-ocp-hybrid-environment/reconciliation-and-corrections.md:41` and `.memlog.md:15`, which had no story and no ledger key; the Dream's own criterion is the Python-side knob, which exists nowhere in `src/platform/` today (fleet readiness 2026-09-09, stA-B14)

### Story 48.3: R-19 network baseline
**Type:** feat • **Effort:** M • **Deps:** — • **FR/AD:** `DW-RT-2026-09-02-3` • red-team X-4, X-6
**Surface:** chart `templates/networkpolicy-*.yaml`, `serviceaccount.yaml`
**Given** the namespace today admits any egress **When** a default-deny NetworkPolicy lands with explicit allows per workload and `automountServiceAccountToken: false` **Then** the platform, worker, sidecar and mcp-host pods still reach exactly their declared peers on CRC, proven by a chart invariant test and an attended bring-up note

### Story 48.4: R-20 secrets profile
**Type:** docs+feat • **Effort:** M • **Deps:** — • **FR/AD:** `DW-RT-2026-09-02-4` • red-team X-7 • `canopy:AD-19`
**Surface:** `docs/reference/enterprise-deployment.md`, `src/platform/deploy/overlays/` (an `ExternalSecret` example), `pyforge-steward` keys runbook
**Given** age key custody is undocumented **When** the profile lands **Then** it states age key custody and rotation, ships one `ExternalSecret` example for the Vault/ESO profile, and a rotation runbook for `DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, the DB roles and the assertion PEM with dual-key verify during rotation

### Story 48.5: R-21 observability contract
**Type:** feat • **Effort:** M • **Deps:** — • **FR/AD:** `DW-RT-2026-09-02-5` • red-team A-7, B-5
**Surface:** `src/platform/config/observability/`, chart alert rules, `pyforge-doctor` flag kill-switch write path
**Given** no SLO is declared **When** the contract lands **Then** SLOs exist for `/ht/`, MCP p99, queue age and event lag, alert rules render from the chart, and Doctor's flag kill-switch has a metrics write path

### Story 48.6: R-22 live browser streaming, or the pillar deleted
**Type:** decision+feat • **Effort:** M • **Deps:** — • **FR/AD:** `DW-RT-2026-09-02-6` • red-team T-8 • CAP-8
**Surface:** `django_pyforge/events/`, a Channels consumer, or the Dream's pillar text
**Given** `/ws/events/` is a Dream pillar with no implementation **When** this story runs **Then** either a Channels consumer over redis-broker Streams with per-`sub` filtering ships behind the `pyforge-steward[dashboard]` extra, or the pillar is deleted from the Dream with a dated operator ruling — one or the other, recorded in the same story

### Story 48.7: The CAP-axis namespace pass
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** Spec Constraints (2026-09-09) • review § 1.3
**Surface:** `ARCHITECTURE-SPINE.md` satellites (foundry → `fnd:`; bmad-suite → `suite:`; secure-live-dashboards → `sld:`), `epics.md` Epics 9, 39, 45–47, `resilience-invariants.md:25,:106`, the AD-citation check, **`stack.md`** (`scripts/pixi_env_matrix.py::render_markdown` is its generator)
**Given** `b8b142db63` normalised ADs and FRs and left ~185 bare `CAP-n` citations in non-canopy satellites **When** the same pass runs on the CAP axis, scoped by satellite range **Then** no non-canopy satellite cites a bare `CAP-n`, the six double-prefix artifacts and two space-form stragglers are cleaned, and `ad_citation_check` gains the CAP form so the regression cannot recur
**And** the same pass closes the **document-tier residue** the 2026-09-09 currency review left unvesselled (fleet readiness, stB-F2/D6/D7): `stack.md`'s `## Absent — feedstock work, blocking` table is retitled and dated as historical — all six rows shipped in `ed41099205` (2026-08-25), including the `cachebox` row whose premise is wrong (conda-forge ships 5.2.3, pinned at `pixi.toml:240`), and the Unifying SPEC's dangling `surface:` glob `recipes/cachebox/**` goes with it; the **High-Leverage matrix**'s five aspirational rows and three wrong-station bindings are corrected (`stack.md:68` binds `graphviz2drawio` to herald — **false**, zero hits in herald, it is an atlas prototype); the **broken regeneration command hardcoded in `scripts/pixi_env_matrix.py::render_markdown`** is fixed at its source, since it is re-stamped on every regeneration and so self-heals into staleness; the `pyforge.*` **import-rule violation** is recorded with its two named carve-outs (`src/platform/ingest/github_projects/` at 8 sites outside the import-linter's `root_packages`, `src/platform/pyproject.toml:288-289`; `django-atlas`'s portal under the `test_station_portal_shells.py:113` allow-list) rather than left as an absolute live code contradicts; and **"16 of 18 living names bind to nothing"** is either corrected or dated as aspirational — never left reading as fact

### Story 48.8: The Single-Spec merge
**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** Dream Grounding "Single-Spec merge — parked"; Spec § Residual • `fnd:AD-18`
**Surface:** `spec-pyforge-unifying-strategy/SPEC.md` (inherited-host table → full `pap:CAP-1..145` text), `specs/spec-python-agent-platform/SPEC.md` (`absorbed-into`), Epic 10–12 citations in `epics.md`, `convergence.md`, **plus the six artifacts that name the parent and were omitted** (fleet readiness 2026-09-09, stA-B13 / stB-B9): the four sibling Specs whose own frontmatter reads `absorbed-into: spec-python-agent-platform` and would otherwise become pointers to a superseded pointer — `spec-asgi-multiplexer-monolith/SPEC.md:5`, `spec-db-gpt-django-plugin/SPEC.md:5`, `spec-enterprise-multi-agent-orchestration/SPEC.md:5`, `spec-langflow-django-plugin/SPEC.md:5`; steward's own spine `architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md:281,:617` (parent pointer + the `pap:AD-n` citation form); and — **cross-station, a relay not an edit** — `_bmad-output/projects/pyforge-mason/…/spec-django-accelerator-framework/SPEC.md:11,:95`
**Given** the operator's 2026-09-09 ruling ("now, before any 44.x flip") **When** `pap:CAP-1..145` full text is copied into the Unifying SPEC, Epic 10–12 citations retarget to `pap:CAP-*` / `pap:AD-*`, and the parent Spec is superseded **Then** `dream-chain-check` and `chain-completeness-check` stay green, `extends:` is retired, and **`[feature.python-agent-platform]` is not renamed** — that is a separate named story if ever
**And** the story states as a rule that **`pap:` stays a live id prefix** — 280 citation sites across 60 files and four other stations (`_bmad-output/projects/pyforge-{doctor,marshal,mason,scribe}/…`, `AGENTS.md`, `pixi.toml`), with `scripts/ad_citation_check.py:123-124` special-casing it in its lookbehind; the merge moves the **TEXT**, never the namespace, and folding `pap:` into `canopy:` is the exact namespace collapse Story 48.7 exists to undo
**And** the parent Dream's two knowingly-false lines are fixed **before or inside** this merge, never carried forward by it: `docs/dreams/python-agent-platform.md`'s "no `src/platform/` tree" claim (struck through and dated 2026-09-09) and its absolutely-stated `pyforge.*` import ban — a regeneration over dangling parents and false absolutes is the failure the drill exists to catch, and 48.8 explicitly precedes that drill

### Story 48.9: OIDC default profile — Keycloak in-cluster, BYO seam kept
**Type:** decision+feat • **Effort:** M • **Deps:** S-48.4 • **FR/AD:** `spec-platform-fifteen-factors` CAP-1 (production half) • fleet readiness 2026-09-09, stB-B1 • co-decided with Story 49.6
**Surface:** `src/platform/deploy/charts/platform/templates/` (a Keycloak `Deployment` + `Service` + its chart values), `src/platform/config/settings/production.py`, `src/platform/config/settings/base.py:564-580` (`COMPONENT_OIDC_*`), `docs/reference/enterprise-deployment.md`
**Given** the `COMPONENT_OIDC_ISSUER` / `_CLIENT_ID` / `_JWKS_URL` / `_AUDIENCE` seam exists and is entirely unpopulated — all four default to `""` at `base.py:564-580`, `production.py` overrides none of them, and `IDP_CLAIMS_SNAPSHOT` / `IDP_USERINFO` are `None` at `base.py:214-215` — while the local substrate is already realm-as-code (`src/platform/compose/keycloak/realms/platform-realm.json`) **When** Keycloak is promoted to an in-cluster deployment by the Foundry chart as the **default** OIDC profile **Then** a chart-rendered deployment authenticates through it end to end, and the `COMPONENT_OIDC_*` seam remains the **BYO-IdP escape hatch** with a documented profile for an external IdP
**And** the story states explicitly that this is **not an infra-kinds breach**: Keycloak is a chart `Deployment` and stores its state in the **existing PostgreSQL**; the lock (PostgreSQL + Redis + Kubernetes) is on backing services, and no fourth kind is introduced
**And** it is decided **together with Story 49.6** — one deployment decision, not two: 49.6 sets the claims source in the deployed default, and this story names the provider that source points at. An external SaaS IdP was rejected as the default because an air-gapped estate cannot reach one, which would force a second profile anyway (`pap:CAP-6` air-gap parity)

### Story 48.10: The one-container Guild proves itself at build time — CI builds the root Containerfile
**Type:** feat • **Effort:** S • **Deps:** — • **FR/AD:** `spec-unified-container` CAP-5 • fleet readiness 2026-09-09, stB-B7 • **before Story 44.10**
**Surface:** `.github/workflows/pyforge-station-tests.yml` (a `container` job, or a pixi `guild-image-build` task the workflow invokes), `pixi.toml` (the build task beside `pyforge-steward-container-gates-test` at `:556` and `-container-volumes-test` at `:569`), `Containerfile` (root) if the build surfaces a defect
**Given** the root `Containerfile` is 14 KB, current, and covers all eight stations — and is referenced by **no** workflow and **no** pixi task (`grep -rn "Containerfile" .github/workflows/*.yml` matches only `src/platform/Containerfile` and the two sidecar files; `pixi.toml` contains no `docker build` / `podman build`), while `pyforge-steward-container-gates-test` and `-container-volumes-test` appear in **zero** CI jobs **When** a job or pixi task invoked by `pyforge-station-tests.yml` builds the root `Containerfile` and runs `scripts/container-gates secrets-scan` + `container-volumes` against the result **Then** CAP-5 — "the image proves itself at build time" — has a build time, and a regression in the image fails CI instead of failing silently
**And** it mirrors the existing docker/podman matrix shape at `platform-ci.yml:305-375` rather than inventing one; the cost is a job, not a design, because the gates already exist and are simply never invoked
**And** it lands **before Story 44.10**, which disables this repo's CI — otherwise the window closes and an unbuilt image is exactly what the regeneration drill (`fnd:AD-18`) reproduces faithfully and silently

### Story 48.11: The platform image can import the warden engine it calls
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** warden readiness 2026-09-09, warden-B7 / warden-E4 • fleet readiness § 2.3 C7
**Surface:** `pixi.toml` `[feature.python-agent-platform.dependencies]` (add `pyforge-warden = { path = … }`, the same shape as `pixi.toml:181`), `environment.yaml` (regenerated — this sync check is **ungated** by the `maintenance` label), a platform-env import test
**Given** `tasks.py:97-102` lazy-imports `pyforge.warden.cli` while the platform image installs only `python-agent-platform`, whose sole path dependency is `pyforge-steward` — so every warden job lands `FAILED` at import time **When** `pyforge-warden` is added as a path dependency of the platform feature and `environment.yaml` is regenerated (`pixi project export conda-environment -e build > environment.yaml`) **Then** `python -c "import pyforge.warden.cli"` resolves inside the platform environment, a test asserts it, and the compliance job runs instead of failing
**And** the PR carries the `maintenance` label **and** the regenerated `environment.yaml` — the label does not suppress the env-sync check

## Epic 49: Shipped becomes in effect (spec-pyforge-unifying-strategy — the realization gate)

**Spec binding.** Decomposes the Constraints block *Correct-course 2026-09-09* (the `verified:`
line; Dreams flip on effect) and Dream § *Where next — The realization gate*. Binding home is the
open question `realization-gate-home`: bound here today (operator 2026-09-09: "Unifying now,
re-home later"); re-homes to `hub:CAP-*` on `spec-intelligence-hub` by memlog once that Spec is
`ready` — story text unchanged. **Widened 2026-09-09 (fleet readiness § 2.3 C6, operator-approved):**
the gate no longer covers only this chain's CAPs. The pass found twelve more `done`-but-not-in-effect
capabilities across five other stations; their **effect stories land on the owning station's own
epics** (marshal Epic 33; atlas, herald, mason, scribe each a small epic), and this epic carries only
an **index row per station** (Stories 49.9–49.13) so one board shows the gate. Doctor gets no index
row — its relay is Story 49.2. **HARD boundaries:** no story reopens a shipped epic or re-mints a
shipped CAP; each exercises a criterion the Spec already states; `capability-effect-check` is
advisory and never a second PR verdict; 49.1 → 49.2 precede 49.3–49.8; **Stories 49.9–49.13 are
index rows only — steward tracks, and never edits another station's surface**, which is the
`spec-surface-check` hazard the alternative (everything under Epic 49) would have created.

### Story 49.1: The verified column on every capability
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** Spec Constraints (2026-09-09) • review § 1.4
**Surface:** `spec-pyforge-unifying-strategy/SPEC.md` § Capabilities (CAP-1..145)
**Given** the review's per-CAP grading with file:line evidence **When** each capability gains a `**verified:**` line **Then** it names which success clause has a live exercise (artifact, deployed check, measured number) and which is fixture-only, with file:line; eleven read fully verified today and six read partial, and the line is the input `capability-effect-check` reads

### Story 49.2: The capability effect check
**Type:** feat • **Effort:** S • **Deps:** S-49.1; cross-station: doctor's own Dream + Spec for the implementation (ledger `blocked` until doctor's story lands — never a foreign-station `Deps:` token) • **FR/AD:** Spec Constraints (2026-09-09) • doctor advisory doctrine • fleet readiness 2026-09-09 § 2.3 C8
**Surface:** this Spec's `verified:` column (the **criterion** stays here). The implementation lives in doctor's own chain and is **named as a relay, never edited by steward** — Dream `docs/dreams/capability-effect-check.md`, Spec `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-capability-effect-check/`, code at `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` (a new source), `pixi.toml` (`detectors` membership), doctor `report-schema.json` (additive)
**Given** 49.1's column **When** `capability-effect-check` runs **Then** it reports every capability whose ledger stories are all `done` but whose `verified:` line names an unexercised clause — advisory, exit-code domain unchanged, never a second PR verdict — and runs in `detectors` beside `story-status`
**And** the check's **input is widened beyond this Spec's own CAP list** to every station's Specs: the pass that minted this story found the five worst cases in steward's *own* satellites (`unified-container`, `secure-live-dashboards`, `ocp-as-a-portability-profile`, `scratch-worktree-lifecycle`, `multi-repo-workspaces`), none of which is a Unifying CAP — a detector scoped to CAP-1..145 would be built to miss its own station on day one (fleet readiness 2026-09-09, stB-D1)
**And** it adopts the cheapest effect test the pass found: **"has a caller outside its own test file"** (fleet readiness 2026-09-09, mars-B-E6 / Class D D4)
**And** the **implementation is relayed to a new doctor Dream + Spec** (fleet readiness § 2.3 C8): every other doctor Source came through doctor's own chain, and `sources/bmad_method.py:9-20` is doctor's own precedent for a dedicated module. **Doctor records the incoming surface claim in `spec-pyforge-doctor`'s memlog BEFORE any code lands**, otherwise `spec-surface-check` reds this story and 49.8 at merge. This story closes when doctor's story lands; it is minted `blocked` until then
**Status:** done
**Outcome (2026-09-13):** doctor's Stories 21.9/21.10/21.11 shipped `sources/capability_effect.py` (`c27e8386d8`, `2bb7bc58f5`, `b2e5b9e948`); `docs/dreams/capability-effect-check.md` and its Spec are now `realized`/`shipped` with `verified:` lines on all three CAPs, including confirming the widened-beyond-this-Spec's-own-CAP-list clause against live code (`iterdir()` over every `_bmad-output/projects/*`, not a hardcoded list). Live run: 396 findings, exit 0. `pyforge-doctor-test -k capability_effect` 30/30 pass. Ledger was never flipped after the work landed; 49.8 was already closed separately (`96387a0730`).

### Story 49.3: CAP-4 in effect — start and get on all eight, with a real disconnect
**Type:** feat • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-4 (`SPEC.md` success) • Stories 21.3 / 21.4 shipped the mounts
**Surface:** the six station MCP faces without `start`/`get`, `django_pyforge/mcp_dual_era.py`, a transport-interrupting test
**Given** `start`/`get` exists on atlas and warden only and the disconnect test never interrupts transport **When** the six other faces gain the pair over the same durable store and a test drops the connection mid-op across a multi-minute run **Then** the agent retrieves the result after reconnect on every station, and CAP-4's `verified:` line reads fully exercised

### Story 49.4: CAP-7 in effect — the real board, or the criterion says fixture
**Type:** feat+decision • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-7 (`SPEC.md` success) • Epic 23
**Surface:** `django-atlas/src/django_atlas_portal/board.py`, `pyforge/atlas/dashboard/`, `test_host_board_row_isolation.py`, `src/platform/config/settings/base.py` (`INSTALLED_APPS`), `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/**` (adopter wiring), `convergence.md:38,:129`
**Given** the isolation test runs against a 5-row in-process fixture and asserts the real Vizro/BSL board is not mounted **When** this story runs **Then** either Atlas's real board is reachable through the host under the isolation pattern with the same two-users test passing against it, or CAP-7's success criterion is rewritten to name the fixture as the deliverable with a dated ruling — one or the other
**And** the **`secure-live-dashboards` adoption decision rides with it, as one decision, not two** (fleet readiness 2026-09-09, stB-B6 / § 2.3 C15): if the real board is mounted, this story **installs `pyforge.steward.dashboard` in `INSTALLED_APPS`** and routes the board's loads through `audit` + `export` — today the app is in no `INSTALLED_APPS` (`base.py` has zero `dashboard` matches), so `AuditEntry` (`models.py:43`, `migrations/0001_initial.py`) has no table anywhere and six of nine modules (`middleware`, `audit`, `views`, `navigation`, `models`, `export`) have zero consumers; if instead the criterion is rewritten to name the fixture, then `spec-secure-live-dashboards`' **Django half is rewritten as deferred in the same act**
**And** the accuracy correction lands with it: `convergence.md:38,:129`'s "never adopted" becomes **"adopted at fixture grade (`django-atlas/board.py:17-20`, a 5-row in-process fixture); the real Vizro board (`pyforge/atlas/dashboard/app.py`) imports zero steward modules"** — the old wording understates what exists and would send an implementer to build a seam that is already there

### Story 49.5: CAP-11 in effect — the eviction test
**Type:** test • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-11 (`SPEC.md` success) • Story 40.2
**Surface:** `src/platform/tests/` (a real-Redis test), chart `hpa.yaml` if 48.2 has not landed it
**Given** the chart split is real and no test fills the cache **When** a test fills `redis-cache` to its `allkeys-lru` limit while tasks are queued on `redis-broker` **Then** no queued task, stream entry or PEL entry is lost, and the test fails without the split

### Story 49.6: CAP-12 in effect — revocation on the next request
**Type:** feat • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-12 (`SPEC.md` success) • Story 26.1 deferral
**Surface:** `src/platform/config/settings/base.py:214-215`, `production.py`, `platformapp/users/current_claims.py`
**Given** `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None` in the deployed default so revocation lands on the next login **When** the claims source is set in the deployed default with a bounded cache **Then** revoking a role at the IdP removes portal access on the user's next request, proven by a test that fails on the login-time path
**And** it is decided **together with Story 48.9** — one deployment decision, not two: 48.9 names the provider (Keycloak in-cluster as the default profile, `COMPONENT_OIDC_*` kept as the BYO seam) and this story sets the claims source that points at it. Neither story may name a provider the other contradicts (fleet readiness 2026-09-09, stB-B1)

### Story 49.7: CAP-14 in effect — real semantic recall, or the criterion says lexical
**Type:** feat+decision • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-14 (`SPEC.md` success) • Story 34.5 • `query-plane-scribe-cutover`
**Surface:** `pyforge-scribe/src/pyforge/scribe/embeddings.py`, `graph_store_plugins.py`, the plane `vss` index
**Given** "semantic" recall is a 32-dim SHA-256 bag-of-concepts over a hardcoded 7-entry synonym map, off by default (`recall.py:94` `mode="lexical"`; `cli.py:316-320` opt-in `--semantic`), while CAP-14's *other* clause — "the same graph operations pass against both drivers" — is already satisfied and exercised in CI (`conftest.py:119-138` parametrized over both drivers; `pyforge-station-tests.yml:215-238` pgvector service) and single-plugin selection is the documented design (`graph_store_plugins.py:36-39`, AD-1), not a shortfall **When** this story runs **Then** either recall is backed by a real embedding model over the plane's `vss` index with a test that lexical overlap fails, or the criterion is rewritten honestly — and in either branch the story states which mode (`lexical` or `semantic`) the criterion is graded against, and records that the Spec's "dual-write" wording mis-described a correct design rather than naming a gap (scribe readiness pass 2026-09-09, E-1)

### Story 49.8: CAP-17 in effect — marshal publishes run state to the supervisor
**Type:** feat • **Effort:** M • **Deps:** S-49.1; cross-station: marshal Epic 33's Track story (ledger `blocked` until it exists — never a foreign-station `Deps:` token) • **FR/AD:** CAP-17 (`SPEC.md` success) • `hub:CAP-3` (the Track, on `spec-intelligence-hub`) • token-economy CAP-7 (savings telemetry — whose five per-layer getters are stubs today, `harness_bmadloop.py:1875-1898`)
**Surface:** `pyforge-marshal` (a publisher toward `django_pyforge.supervisor` — the same seam as the Track and savings telemetry), `pyforge-doctor/sources/marshal.py:544`, `marshal/cli/init.py:331`
**Given** the supervisor carries MCP-`start` runs only while marshal has zero imports of `django_pyforge` and reads `~/.bmad-loops` **When** marshal publishes bmad-loop run state through one publisher shared with Epic 33's Track **Then** the front door shows a live bmad-loop run in a deployed namespace with no operator-home access, a completed run's timing survives the workstation, and marshal and doctor no longer read `~/.bmad-loops`
**And** it carries the one-line comment at `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py:223` noting that the `~/.bmad-loops` read retires under Unifying CAP-17 — **doctor minted no separate story for it**, so that comment plus the memlog line on `spec-pyforge-doctor` is doctor's whole action here (fleet readiness 2026-09-09, § 2.3 C8)


### Story 49.9: Index — marshal realization-gate effect stories
**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: marshal Epic 33 (ledger `blocked` until that epic closes — never a foreign-station `Deps:` token) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Marshal's own `epics.md` / Specs are **named, never edited** by steward
**Given** four marshal capabilities are `done` and not in effect — `adaptive-model-tiering` (fed on 2 of 8 stations; the floor-raise applies only on spin), `risk-tiered-review-depth` (zero callers outside `tests/unit/test_gate.py`; `core/gate.py:724,:768`), `marshal-parallel-dispatch-fanout` (`max_parallel = 1` everywhere, `cli/dispatch.py:902`; no live wave has run), and the two Epic-20 watchdogs plus Story 3.12's floor-raise, which observe `~/.bmad-loops` and have been dormant since 2026-08-22 **When** marshal's Epic 33 lands their effect stories (the `bmad-correct-course` already scheduled there also carries token-economy CAP-18 and the risk-tiered wiring story) **Then** this row flips `done` and `capability-effect-check` stops reporting them
**And** steward's only action is this row plus the citation — the work, the surfaces and the retro are marshal's
**Status:** done
**Outcome (2026-09-13):** marshal's own ledger confirms Stories 33.5 (risk-tiered-review-depth producer+caller), 33.6 (adaptive tiering fed on all eight stations), 33.7 (Epic-20 watchdogs observe the real plane), and 33.8 (first live fan-out wave) are all `done`. Citing marshal Epic 33 as closed for these four capabilities; ledger was never flipped after the work landed.

### Story 49.10: Index — atlas realization-gate effect stories
**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: atlas's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C1 / C6
**Surface:** this file only (the index row). Atlas's own artifacts are **named, never edited** by steward
**Given** `atlas-query-dashboards` shipped a second Lane-3 runtime at `pyforge/atlas/views/` (Epic 14, CAP-1..145, 4/4 `done`) that nothing reaches — no CLI verb, pixi task, ASGI mount or portal imports it, only `tests/unit/views/*` — and it reads the legacy SQLite store through a dynamic-import bridge whose own docstring declares the evasion of CAP-19's "no private DuckDB" ruling (`cli_bridge.py:11-17`) **When** atlas records the **retirement** (operator ruling C1: delete the package + tests, record the supersession on its Spec, keep the widget-registry idea only if a Vizro page wants it) **Then** this row flips `done`; the Unifying Dream's Kinships line has already been corrected here to say `retired 2026-09-09`
**And** the live Lane-3 runtime is and remains the Vizro/BSL board (31 pages)
**Status:** done
**Outcome (2026-09-13):** confirmed shipped 2026-09-10 via atlas Story 25.1 (PR #1114, `caeae255d05`) — `pyforge/atlas/views/`, its tests, and `cli_bridge.py` are all deleted (verified: zero repo-wide importers outside this Spec's own narrative text), `docs/dreams/atlas-query-dashboards.md` is `status: archived` with a Realization log entry, and `spec-atlas-query-dashboards/SPEC.md` marks CAP-1..CAP-4 `SUPERSEDED`. Ledger was never flipped after the work landed.

### Story 49.11: Index — herald realization-gate effect stories
**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: herald's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6 / C11
**Surface:** this file only (the index row). Herald's own artifacts are **named, never edited** by steward
**Given** three herald capabilities are `done` and not in effect — the live backend (`herald-live-demo.yml` is `disabled_manually` with 100 of 100 runs failed, last run 2026-08-24, and its store is `runner.temp`), the deck-QA gate (called by nothing), and the pptx pipeline (has never rendered a station deck) **When** herald lands their effect stories, or re-scopes them as a *hosting* decision deferred until the Foundry gives Herald a perimeter (steward's `deploy perimeter` cannot target an arbitrary ASGI callable today, `deploy.py:484`) **Then** this row flips `done`
**And** steward records only the dependency: the perimeter is a Foundry capability, so herald's hosting branch is gated on steward's chart work, not on this row

### Story 49.12: Index — mason realization-gate effect stories
**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: mason's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Mason's own artifacts are **named, never edited** by steward
**Given** the `pyforge-mason` recipe verb family is `done` and unreachable — `mason doctor` reports `unavailable_verbs: ('recipe',)` because `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`, two lines) lacks the `truststore` + `conda-forge-metadata` floor `cfe.py:180-186` requires, and nothing in the estate invokes `mason recipe|package|environment` **When** mason lands the dependency fix and one real invocation **Then** this row flips `done`
**And** the fix touches `pixi.toml`, which is steward-adjacent: if the dependency lines are added in a steward PR, that PR **regenerates `environment.yaml`** (ungated by the `maintenance` label) — named here so the obligation is not discovered at CI
**Status:** done
**Outcome (2026-09-13):** landed as a side effect of `spec-library-catalog-manifest-sync` (marshal Epic 36, PR #1291, `8beb582d30`) — `truststore >=0.10.4` and `conda-forge-metadata >=2026.9.10` are both now in `[feature.pyforge-mason.dependencies]`. Confirmed live: `mason doctor` reports `unavailable_verbs: ()`, and the `pyforge-mason-recipe-build-smoke` task (already wired into `pyforge-station-tests.yml`'s mason-test job) is the real invocation — `pixi run -e pyforge-mason pyforge-mason-recipe-build-smoke` builds `recipes/click-help-colors` via `mason recipe build`, `returncode: 0`, artifact produced. Ledger was never flipped after the work landed.

### Story 49.13: Index — scribe realization-gate effect stories
**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: scribe's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Scribe's own artifacts are **named, never edited** by steward
**Given** scribe's scheduled compile is `done` and not in effect — the store was last written 2026-08-27 and the "nightly" schedule is a hand-installed crontab line, not a declared, reproducible surface **When** scribe lands the effect story (a declared schedule the estate can see and a recorded run) **Then** this row flips `done`
**And** steward records the placement question only: a scheduled compile that must survive the cutover is a Foundry-side surface, not a workstation crontab

### Story 49.14: CAP-10 in effect — the resilience primitives get a real caller, or the criterion says test-only
**Type:** feat+decision • **Effort:** M • **Deps:** S-49.1 • **FR/AD:** CAP-10 (`SPEC.md` success) • `resilience-invariants.md` BS-4 / BS-8
**Surface:** `src/platform/config/` (the inter-station HTTP client, the PyBreaker async wrapper's call site), `pyforge-mason/src/pyforge/mason/boot.py` (confirm the reconciliation path is live on the real boot sequence, not only its own test), `spec-pyforge-unifying-strategy/SPEC.md` (CAP-10's own success text, if tightened)
**Given** the circuit breaker (`django_pyforge.circuits`, BS-4) and boot reconciliation (`reconcile_boot`, BS-8) each pass their own dedicated meta-test (`test_circuits_trip_on_async_too.py::test_removing_wrapper_makes_the_test_fail`, `test_restarts_reconcile.py::test_removing_reconciliation_makes_the_test_fail`) — satisfying CAP-10's own written bar, "an invariant with no test that fails in its absence is not implemented, however much code exists" — but `grep -rln "django_pyforge.circuits" src/` and a search for `reconcile_boot` callers both return zero hits outside their own test files, so neither mechanism protects anything in a real failure today, the identical shipped-but-inert shape CAP-4/7/11/12/14/17 were each given a story to close
**When** this story runs **Then** either a real call site is wired to each (the inter-station HTTP client for the breaker; confirmed live on Mason's actual boot path for reconciliation, not only its test) and CAP-10's own success criterion is tightened to require a production caller, matching its five siblings, **or** the criterion is formally kept test-only with a dated, stated reason why CAP-10 is deliberately held to a different bar than the other six
**And** whichever branch is taken, `resilience-invariants.md`'s BS-4/BS-8 rows and `SPEC.md`'s own CAP-10 text are updated to match — the two must never read differently again


## Currency validation note — 2026-09-05

`arch→epics` cascade after the steward PRD and ARCHITECTURE-SPINE re-dated to 2026-09-05
(`spec-pyforge-steward`'s two same-day memlog motions + the new `spec-bmad-eval-quality`).
Validated against the re-dated spine: no AD added or changed. The only structural delta since
the 2026-08-31 review is Epic 45 (Stories 45.1 / 45.2), decomposing `spec-bmad-eval-quality`
CAP-1 / CAP-2; its story keys are present in `sprint-status-ledger.yaml` (`45-1-…` in-progress,
`45-2-…` blocked, `epic-45` backlog). No story text altered.

## Currency validation note — 2026-09-06

`spec→prd→arch→epics` cascade for the new chain `spec-bmad-suite-lifecycle` (Dream `docs/dreams/bmad-suite-lifecycle.md`, PRD `prd-bmad-suite-lifecycle-2026-09-06`, spine `architecture-bmad-suite-lifecycle-2026-09-06`, all 2026-09-06). Structural delta: Story 14.9 (core-upgrade CAP-9 `--no-shims`), Epic 46 (Stories 46.1–46.10, CAP-1..145) and Epic 47 (Stories 47.1–47.5, CAP-9), hand-authored mirroring Epic 45; every new `### Story` heading maps 1:1 to a `sprint-status-ledger.yaml` key minted by `sprint_plan.py generate` + scoped `sprint-ledger-sync` the same day. Ledger corrections the same day: 14-6/14-7/14-8 `backlog → done` (code on main since PRs #1074/#1076), 45-2 `blocked → backlog` (operator flip 2026-09-06). Validated against the steward spine (no AD changed) and the lifecycle spine AD-1..AD-8; no existing story text altered.


## Currency validation note — 2026-09-08

`arch→epics` cascade closing the 2026-09-08 `spec→prd` staleness edge (spec-pyforge-steward's
`.memlog.md` moved for the deferred-work sweep follow-ups while the PRD's stamp sat at
2026-09-05). Validated against `ARCHITECTURE-SPINE.md` as re-dated 2026-09-08: **no AD added or
changed.**

One Story added, in an existing epic rather than a new one: **Story 43.7 — Sidecar runtime
validation on Python 3.14.** `mason/DW-13-2-2` had deferred the dbgpt-sidecar Celery REST
round-trip and SQLite metadata-store validation to Story 43.6; 43.6 closed `done` with acceptance
criteria covering only the pin flip, the re-lock, the regenerated `environment.yaml` and an
`import pyforge.atlas, pyforge.doctor` smoke. A search of this file for `Celery REST`,
`round-trip` and `SQLite metadata` returned nothing in any story, so the validation was unowned,
not merely late — 43.6 can never pick it up again. 43.7 owns it and decomposes the existing
`pap:CAP-5` / `pap:CAP-6`; the mason ledger entry's `location:` now points at it.

The blocker that caused the original deferral is recorded as closed rather than assumed: the
entry cites `dbgpt-ext-rag`'s `onnxruntime <=1.18.1` cap as having no cp314 build, but
`pixi list -e dbgpt-sidecar` resolves `python 3.14.7`, `dbgpt-app 0.8.2`, `dbgpt-ext-rag 0.8.2`
and `onnxruntime 1.28.0 py314h112547c_0_cpu` (verified live 2026-09-08). 43.7 waits on no solve;
what is missing is runtime coverage — `platform-ci`'s `container-dbgpt` job polls `/api/health`
for 200 and asserts nothing else.

Ledger: `43-7-sidecar-runtime-validation-on-python-3-14: backlog`. Every Story heading in this
file still maps 1:1 to a `sprint-status-ledger.yaml` key.


## Currency validation note — 2026-09-09

`spec→prd→arch→epics` cascade for `bmad-correct-course` on `spec-pyforge-unifying-strategy`
(`SPEC.md` `updated: 2026-09-09` — `:488` amended by operator ruling, `:73`/`:315` floor corrected,
Constraints block *Correct-course 2026-09-09*, § Residual (2026-09-09), two `open_questions`).
Structural delta: **Epic 48** (Stories 48.1–48.8) and **Epic 49** (Stories 49.1–49.8), hand-authored
mirroring Epic 47; every new `### Story` heading maps 1:1 to a `sprint-status-ledger.yaml` key
minted by `sprint_plan.py generate` the same day (20 new keys, 0 changed, 14 `blocked` preserved
sticky). Epic 44's heading paragraph gained the 2026-09-09 order amendment (47's P-lines before
44.3; 48.1 before any ledger write; 48.8 before the regeneration drill). Validated against the
steward spine as of 2026-09-08: **no AD added or changed** — 49.1's `verified:` column is a Spec
shape, not an AD; Epic 49's binding home is the Spec's open question `realization-gate-home`.
**No `sprint-ledger-sync` was run and none may run on this project until 48.1 lands.** Record:
`sprint-change-proposal-2026-09-09-currency-review.md`.

## Currency validation note — 2026-09-09 (fleet readiness)

Second 2026-09-09 cascade, applying the **operator-approved** decision batch
`research/fleet-readiness-decision-batch-2026-09-09.md` (eight read-only agents graded all 96 live
Dreams against `main` `fe4025ea90`; every row in its § 2 is approved, § 4 is the apply order).
Scoped to Epics **48** and **49**; **no other epic's text was altered** and no shipped CAP was
re-minted.

Structural delta — six new stories, all in existing epics:
**48.9** (OIDC default profile — Keycloak in-cluster, `COMPONENT_OIDC_*` BYO seam kept; C7/stB-B1,
co-decided with 49.6), **48.10** (CI builds the root `Containerfile` and runs the two container
gates; C7/stB-B7, due before 44.10 closes the CI window), **48.11** (`pyforge-warden` path dep in
the platform env + regenerated `environment.yaml`; C7/warden-B7), and index rows **49.9–49.13**,
one per station whose satellites gained effect stories (marshal, atlas, herald, mason, scribe).
Doctor gets no index row — its relay is Story 49.2.

Amendments to existing stories (text widened, never re-scoped away): **48.1** gains the
station-agnostic construction rule, the `epic-44`…`epic-49` rollup defect, the `AGENTS.md:49`
`--repair-feed` correction and the one-line scratch-worktree landing ritual, and names the marshal
test file (`test_promote_sprint_status_regressions.py:55`) that pins the bug; **48.2** gains the
ASGI thread-pool clause closing the `asgi-multiplexer-monolith` residue; **48.7** gains explicit
**document-tier residue** scope (the obsolete feedstock table, the High-Leverage matrix, the broken
regeneration command in `pixi_env_matrix.py::render_markdown`, the `pyforge.*` import-rule
violation, "16 of 18 living names"); **48.8**'s Surface gains the four `absorbed-into` pointers,
steward's own spine and mason's relay, plus the rule that `pap:` stays a live prefix; **49.2** is
widened to every station's Specs, gains the "has a caller outside its own test file" test, and its
**implementation relays to a new doctor Dream + Spec**; **49.4** absorbs the `secure-live-dashboards`
adoption decision and the `convergence.md` accuracy correction; **49.6** is bound to 48.9 as one
deployment decision.

Validated against the steward spine as of 2026-09-08: **no AD added or changed** — the index rows
are tracking artifacts, and every widened clause exercises a criterion its own Spec already states.
Ledger: keys minted with `sprint_plan.py generate` only (`48-9`, `48-10`, `48-11`, `49-9`…`49-13`),
with `49-2` and `49-9`…`49-13` minted **`blocked`** (cross-station producers — never a foreign
`Deps:` token). **No `sprint-ledger-sync` was run and none may run on this project until 48.1
lands.**

## Epic 50: Object storage is consumable, without pyforge operating it (spec-platform-object-storage-kind)

Minted 2026-09-10 via `bmad-correct-course`
(`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`, seeded from
`docs/dreams/platform-object-storage-kind.md`). **CAP-1** (the AD-1 exception itself) is
**already landed** by that correct-course pass, not a separate story: `spec-pyforge-
unifying-strategy/SPEC.md`'s AD-1 gained a dated, bounded exception bullet — S3-compatible
object storage is permitted **consumed**, never **self-hosted** — production target NetApp
StorageGRID (ops-provided, externally operated), and `stack.md`'s own "Never" line was
qualified to match. Stories 50.1-50.3 below decompose the Spec's remaining CAP-2..4:
local-dev equivalent Silo (default) / Garage (alternative), both pixi-installable. Does not
reopen Lane 1 media's own RWX-PVC answer (2026-09-05); no consumer is wired to the new
capability in this epic.

### Story 50.1: The Silo conda-forge recipe exists and is pixi-installable

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-platform-object-storage-kind
CAP-2 (`SPEC.md` success)
**Note:** `pgsty/silo` has no conda-forge feedstock today (live-verified 2026-09-10). Recipe work
under `recipes/` is governed by `.claude/skills/conda-forge-expert/` per this repo's Rule 1 —
this story invokes that skill for the recipe lifecycle itself; this entry only tracks the story.
**Surface:** `recipes/silo/recipe.yaml` (new), `recipes/silo/` supporting files (patches, tests)
per the CFE recipe-authoring convention.
**Given** `pgsty/silo` ships real, versioned per-platform release binaries (`linux_amd64`,
`linux_arm64`, `darwin_amd64`, `darwin_arm64`, `windows_amd64`, `windows_arm64`) but no
conda-forge feedstock **When** a v1-format `recipe.yaml` is authored wrapping the upstream
release binary for this repo's supported platforms and carried through the full CFE
lifecycle (`validate_recipe`, `optimize_recipe`, `scan_for_vulnerabilities`, a green linux-64
`recipe-build`) **Then** the recipe is genuinely buildable and testable locally
**And** the built package is published to the `SelfExplainML` anaconda.org channel (this repo's
own documented staging path — `commands-cheatsheet.md` § *Publishing to the SelfExplainML
channel*), so it is pixi-installable immediately without waiting on upstream
`conda-forge/staged-recipes` review
**And** submitting to `conda-forge/staged-recipes` for long-term community packaging is named as
the normal follow-up, not a blocker for this story
**Status:** backlog

### Story 50.2: Local-dev object storage — Silo default, Garage alternative, pixi-provisioned

**Type:** feature • **Effort:** M • **Deps:** S-50.1 (Silo must be pixi-installable first) •
**FR/AD:** spec-platform-object-storage-kind CAP-3 (`SPEC.md` success)
**Note:** Mirrors `scripts/scribe_pg.py`'s exact shape (Story 28.1's own local-database
precedent): a real local server, never a mock, `up`/`down`/`status` pixi tasks, gitignored
`var/`-scoped data dir, idempotent. A SEPARATE pixi feature (not folded into `platform-dev`),
matching the `scribe-pg`/pgvector win-64 precedent — Garage has no win-64 build, and folding it
into a feature that inherits the full workspace platform list would break that solve outright.
**Surface:** new `[feature.platform-object-storage]` in `pixi.toml` (`silo` + `garage`
dependencies), `scripts/platform_object_storage.py` (new), `var/platform-object-storage/`
(gitignored).
**Given** neither Silo nor Garage is provisioned anywhere in this repo today **When** the new
pixi feature and script are added, backend selected via `PYFORGE_OBJECT_STORAGE_BACKEND`
(default `silo`, mirroring `PYFORGE_SCRIBE_TRIGGER_BACKEND`'s own pattern) **Then**
`platform-object-storage-up`/`-down`/`-status` pixi tasks start/stop/report a real local
S3-compatible server, idempotently, with data under gitignored `var/`
**And** switching to `PYFORGE_OBJECT_STORAGE_BACKEND=garage` runs the identical lifecycle
against Garage instead, with an honest note that Garage lacks a win-64 build (refuses cleanly
on that platform, never a silent no-op)
**And** a fresh `pixi install -e platform-object-storage` resolves cleanly
**Status:** backlog

### Story 50.3: A minimal S3-client seam proves the exception end-to-end

**Type:** feature • **Effort:** S • **Deps:** S-50.2 • **FR/AD:** spec-platform-object-storage-kind
CAP-4 (`SPEC.md` success)
**Note:** Endpoint and credentials are configuration only, never hardcoded — the same client
code points at the local Silo/Garage instance or real StorageGRID interchangeably, mirroring
`canopy:AD-19`'s reference-not-embed pattern for the external IdP. Explicitly does **not**
migrate Lane 1 media or any other existing feature onto object storage in this story.
**Surface:** one new `src/platform/` module (a thin S3-client wrapper), one round-trip test.
**Given** the exception now permits object-storage consumption but nothing in `src/platform/`
can reach one **When** a minimal client module resolves an endpoint URL + credentials from
configuration (env vars / settings, never hardcoded) and performs a put/get round trip
**Then** the same client code proves out against the local Story-50.2 backend in a test
**And** no existing feature (Lane 1 media, CycloneDX SBOM handling, or anything else) is wired
to consume it in this story — the seam exists and is proven; consumption is separate, future,
story-by-story work
**Status:** backlog

## Epic 51: PostgreSQL and Redis become consumable, without pyforge mandating self-hosting

Minted 2026-09-11 via `bmad-correct-course`
(`sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`, seeded from
`docs/dreams/platform-datastores-consumed-not-self-hosted.md`, the direct follow-up Epic
50's own Non-goals left open — that effort scoped itself to object storage only). **The AD-1
exception itself is already landed** by this correct-course pass, not a separate story:
`spec-pyforge-unifying-strategy/SPEC.md`'s AD-1 gained a second dated, bounded exception
bullet — PostgreSQL and Redis are permitted **consumed**, never mandatorily **self-hosted**,
the same shape already granted to the identity provider and to object storage. Production
target: Enterprise Managed PostgreSQL and Enterprise Managed Redis on the same Enterprise
Managed OCP cluster that already hosts the platform (operator-confirmed 2026-09-11, not
hypothetical). Stories 51.1-51.3 below decompose the remaining work: a BYO-external-endpoint
overlay for each datastore, and the backup/PITR handoff the Postgres overlay creates. **The
existing self-hosted default is not removed or changed by any of these three stories** — each
adds an additional, opt-in overlay; the bundled StatefulSet/Deployment stays the default for
local dev and for any deployment not opting into the BYO overlay. Does not reopen Kubernetes's
own already-external treatment or any already-shipped feature.

### Story 51.1: A BYO-external-PostgreSQL deployment overlay exists, additive to the self-hosted default

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-unifying-strategy
AD-1 datastores exception (`SPEC.md` § Constraints, dated 2026-09-11)
**Note:** Mirrors the existing OCP overlay's own additive shape
(`src/platform/deploy/overlays/ocp/core-overrides.yaml`) — a values file layered with `helm
... -f`, never a rewrite of the base chart. `DATABASE_URL`/`MIGRATION_DATABASE_URL` are
already read via `env()` in `settings/base.py`; nothing at the application layer needs to
change, only what the chart deploys and what values populate those secrets.
**Surface:** new `src/platform/deploy/overlays/external-postgres/` (values overlay +
README), conditional guards in `postgres-statefulset.yaml`/`postgres-service.yaml`/
`postgres-backup-pvc.yaml` (a `.Values.postgres.external.enabled` toggle, default `false`).
**Given** pyforge's own chart unconditionally deploys a self-hosted PostgreSQL
StatefulSet today **When** a new overlay is applied setting
`postgres.external.enabled: true` plus an externally-supplied endpoint and credential
secret reference **Then** the chart deploys zero self-hosted Postgres resources
(`postgres-statefulset.yaml`/`postgres-service.yaml`/`postgres-backup-pvc.yaml` all
render empty) and the application's `DATABASE_URL`/`MIGRATION_DATABASE_URL` resolve to
the externally-supplied endpoint instead
**And** with the overlay NOT applied, a `helm template` render of the chart is
byte-identical to today's output — the self-hosted default is unconditionally
preserved, not just assumed unaffected
**Status:** done

### Story 51.2: A BYO-external-Redis deployment overlay exists, additive to the self-hosted default

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-unifying-strategy
AD-1 datastores exception (`SPEC.md` § Constraints, dated 2026-09-11)
**Note:** Same pattern as 51.1, applied to Redis. `REDIS_URL`/`REDIS_BROKER_URL`/
`REDIS_CACHE_URL` are already read via `env()` in `settings/base.py`.
**Surface:** new `src/platform/deploy/overlays/external-redis/` (values overlay +
README), conditional guards in `redis-deployment.yaml`/`redis-service.yaml`/
`redis-broker-pvc.yaml` (a `.Values.redis.external.enabled` toggle, default `false`).
**Given** pyforge's own chart unconditionally deploys a self-hosted Redis Deployment
today **When** a new overlay is applied setting `redis.external.enabled: true` plus an
externally-supplied endpoint and credential secret reference **Then** the chart deploys
zero self-hosted Redis resources (`redis-deployment.yaml`/`redis-service.yaml`/
`redis-broker-pvc.yaml` all render empty) and the application's
`REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` resolve to the externally-supplied
endpoint instead
**And** with the overlay NOT applied, a `helm template` render of the chart is
byte-identical to today's output — the self-hosted default is unconditionally
preserved, not just assumed unaffected
**Status:** done

### Story 51.3: The backup/PITR handoff is explicit when the BYO-PostgreSQL overlay is active

**Type:** feature • **Effort:** S • **Deps:** S-51.1 (needs the overlay's
`postgres.external.enabled` toggle to condition on) • **FR/AD:**
spec-pyforge-unifying-strategy AD-1 datastores exception (`SPEC.md` § Constraints, dated
2026-09-11)
**Note:** Not a large code change so much as a real, separately-reviewable decision the
Dream deliberately left open rather than pre-deciding — kept as its own story rather than
folded into 51.1 so it gets its own review.
**Surface:** conditional guard on `postgres-backup-cronjob.yaml` (reuses 51.1's
`.Values.postgres.external.enabled` toggle), one new paragraph in
`src/platform/deploy/README.md`.
**Given** `postgres-backup-cronjob.yaml` today runs unconditionally against whatever
Postgres the chart deploys **When** `postgres.external.enabled: true` (Story 51.1's
overlay) **Then** the backup CronJob is not deployed — pyforge's chart does not create a
shadow backup of a database it does not own
**And** `deploy/README.md` gains an explicit line naming the enterprise database team as
the owner of backup/PITR for the BYO-PostgreSQL path, so the handoff is documented, not
silently assumed
**And** with the overlay NOT applied, the backup CronJob still deploys exactly as it does
today — no change to the self-hosted default's backup behavior
**Status:** done

## Epic 52: The last two suite skips become an authoring path and an isolated sidecar

Minted 2026-09-13 from `docs/dreams/suite-scaffold-and-mybmad-sidecar.md`. The
2026-09-06 operator verdict on `spec-bmad-suite-lifecycle` left
`bmad-module-template` and `mybmad-dashboard` at `skip`. This epic flips those
two register rows by Story, not by silent edit: template = authoring tool
beside `bmad-builder`; mybmad = opt-in sidecar on **our Postgres + our OIDC**.
Operator lock the same day: one cluster, **schema `mybmad`** for Prisma; same
Keycloak plane as `/console/`; `src/platform/` grows no second login; mybmad
is not `/console/`. Launcher-local `pg_ctl` + Better Auth is a dev fallback
only. `retired-console-check` stays green. `bmad-dashboard` (member 12) stays
the opt-in marshal VS Code surface. Does not flip any Epic 44 `blocked` key.

### Story 52.1: Module-template is authoring-only and mybmad is an isolated sidecar never the console

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-suite-scaffold-and-mybmad-sidecar
CAP-1..145; spec-bmad-suite-lifecycle CAP-1 (register rows 11 and 13)
**Note:** Wielded path is consume, not isolate. Same `DATABASE_URL` host as
the platform (self-hosted or Epic 51 BYO), `?schema=mybmad`. Same
`COMPONENT_OIDC_*` / Keycloak issuer. Forbidden: second cluster as the
register path; Prisma in Django's schema; Better Auth passwords as estate
login; new login code under `src/platform/`; mount at `/console/`.
**Surface:** `adoption-register.md` rows 11 and 13; lifecycle `.memlog.md` +
`bmad-spec` re-derive of Non-goals; chart/Liquibase (or equivalent) creates
schema `mybmad` only; launcher overlay env for `DATABASE_URL` + OIDC client;
steward docs beside `bmad-builder`. Never `steward provision --module` for
the template.
**Given** rows 11 and 13 still read `skip` on the 2026-09-06 verdict **When**
this story lands **Then** row 11 is `wield (authoring tool only)` with wielder
steward / `bmad-builder`, and row 13 is `wield (sidecar: estate Postgres
schema mybmad + estate OIDC)` with hazard text naming the consume contract
**And** `bmad-spec` has re-derived `spec-bmad-suite-lifecycle` so Non-goals
name authoring-tool + consume-sidecar, not skips
**And** no route or Django include mounts mybmad at `/console/`;
`src/platform/` gains no second login; `retired-console-check` stays green
**And** Prisma migrations apply only in schema `mybmad` on the estate
Postgres; Django/Liquibase objects in `public` (or their existing schema)
are unchanged
**And** mybmad authenticates via the estate Keycloak/OIDC client (no estate
email/password Better Auth); a Keycloak client id for the sidecar is config,
not a new IdP
**And** `pipeline-truth`'s `wired` column still agrees with the register
(template remains unwired-as-module; mybmad remains a sidecar process)
**And** django-pyforge chrome can **show** mybmad (switcher tile and/or
embed) after the same OIDC session, as a surface — not station nine, not
`/stations/mybmad/`, not `/console/`; the process stays the sidecar
**Status:** done

## Epic 53: Intelligence Hub realization (spec-intelligence-hub hub:CAP-1..145)

Minted 2026-09-13 from `docs/dreams/intelligence-hub.md` / `spec-intelligence-hub`
after D4 (Non-goals vs adopt-anytime later-caps). Owner steward; **marshal**
relays `hub:CAP-3` Track field enumeration; **scribe** relays CAP-2 Frame-store
pointers — name them, do not implement marshal/scribe code here unless a
one-line pointer is required. CAP-5 stays mason lane (green local build, no
external PR); do not mint mason stories on this epic. First nine Frames are
Company + eight stations in git; Community Frame and registry are later-caps.
Does not flip any Epic 44 `blocked` key. Does not implement Story 52.1.

### Story 53.1: The Charter carries the Hub vocabulary map

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-intelligence-hub
CAP-1; Charter CAP-4 (external terms never join the seven Lexicon words)
**Note:** Recording document is `docs/dreams/pyforge-charter.md` § The Lexicon
(guild-E3 closed the Unifying Strategy branch). Reverse walk: Lexicon nouns
with no Hub counterpart plus the Cogs collision. Companion
`vocabulary-map.md` stays the working table.
**Surface:** `docs/dreams/pyforge-charter.md`; `docs/governance/spec-pyforge-charter/`
(memlog + re-derive if the Charter Spec must record the amendment); `spec-intelligence-hub/vocabulary-map.md`
**Given** the Hub map lives only in the Spec companion **When** this story lands
**Then** the Charter Lexicon carries the whitepaper→PyForge map and the reverse
block, and states the rented-model / owned-context tension
**And** Frames / Cogs / Ops / Guards / Gates / Tracks / Organizational Memory
do not become an eighth Lexicon word
**Status:** done

### Story 53.2: Company and eight station Frames pass in-repo preflight

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-2 (B9/B11; D4 later-caps)
**Note:** Relay — scribe owns Frame-store half as pointer, not as Lexicon owner.
First nine artifacts only. Community Frame and registry stay later-caps.
**Surface:** Company + eight station `.frame.md` (git store); in-repo four-field
preflight (`type`, `name`, `description`, `visibility` + owner). Do not bind
acceptance to upstream `tools/validate_frames.py`.
**Given** B11 says author now **When** this story lands **Then** one Company
Frame and eight station Frames that `inherits` it exist in git
**And** each passes the in-repo four-field preflight and names its owner
**And** no Community Frame or registry is required for success
**Status:** done
**Superseded by 53.6 (2026-09-14) — do not read the Surface/AC above as current.**
The "four-field preflight … + owner" shape was v0.2-era and is gone: `owner` was
never a Frame element in any version (the field is `maintainer`; see
`DW-VOCAB-2026-09-14-4`), and the preflight now requires **six** — `type`,
`identifier`, `name`, `description`, `visibility`, `maintainer` — keyed on
`identifier`, not `name`. Current shape: `docs/foundry/frames/README.md`.

### Story 53.3: One tracked track.json per run

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-3 (B8)
**Note:** Relay — marshal supplies Track field enumeration. Do not implement
marshal code in this steward story unless a one-line pointer is required.
**Surface:** one tracked `track.json` per bmad-loop / `marshal factory spin` run;
retention: Track indefinite, raw payload 90 days
**Given** a run emits split gitignored evidence today **When** this story lands
**Then** one structured Track record lists Guards, Gates, enumerated fields,
and the stated retention
**And** Guards/Gates are readable from the record, not inferred from policy TOML
**Status:** done

### Story 53.4: Guards as a library without a second verdict

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-4 (B7)
**Given** Source-Grounding exists only at scribe recall AD-8 and Outcome is
absent **When** this story lands **Then** a Spec can name which paper Guard
categories it lacks
**And** Warden stays the sole PR verdict and doctor stays advisory — no Guard
mints a second verdict
**And** Source-Grounding is the first category added to the library
**Status:** done

### Story 53.5: Adopt the frame-spec v0.3 working draft

As a platform operator,
I want the nine git-store Frames and B's first Frame tree to follow the
v0.3 working draft (Apache-2.0),
So that foundry starts as a Hub participant, not a private v0.2 fork.

**Type:** docs • **Effort:** S • **Deps:** S-53.2 • **FR/AD:** spec-intelligence-hub
CAP-2
**Surface:** `docs/foundry/frames/` on A and B; `type: frame [0.3]`;
`license` Apache-2.0 IRI; `identifier` stated. Draft:
openteams-ai/frame-spec#28. Do not open a second LICENSE PR.
Lands in the same kit as 54.1 (case-list) and Epic 55 (strangler ledger).
**Given** #28 adds Apache-2.0 and the v0.3 model **When** this story lands
**Then** every tracked `.frame.md` uses `frame [0.3]` and the Apache-2.0 IRI
**And** B has the nine Frames (writer), not only a PIN path to A
**And** in-repo preflight accepts any `type` whose first word is `frame`
**And** we adjust when #28 / #29 merge
**Status:** done

### Story 53.6: Frame identity is the qualified-ref identifier, not the name

As a platform operator,
I want the nine Frames to satisfy frame-spec v0.3 in full — qualified-ref
identifiers, prose titles, sequence-shaped repeatables — and the preflight to
key off `identifier`,
So that a Hub reader resolves our Frames by the element that carries identity,
and the estate stops using one string as both a Frame key and a dist name.

**Type:** docs • **Effort:** S • **Deps:** S-53.5 • **FR/AD:** spec-intelligence-hub
CAP-2
**Surface:** `docs/foundry/frames/**` (9 files),
`src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py`,
its unit test, `docs/foundry/frames/README.md`, the `frame-preflight` pixi
task description. Operator ruling 2026-09-14: adopt v0.3 now rather than start
from an outdated version — this overrides `spec-vocabulary-one-name-one-job`'s
Non-goal "chasing frame-spec v0.3 before PR #28 merges", which is amended in
the same change.
**Given** 53.5 left the nine Frames on `identifier: pyforge-<station>` (a bare
`name-ref`), slug `name:` values, and scalar `maintainer`/`inherits`
**When** this story lands
**Then** every Frame carries a `qualified-ref` identifier (`pyforge/company`,
`pyforge/<station>`) with exactly one `/` and no `@` (v0.3 §4.2.1, §5.3)
**And** `name` is the Charter's prose form (`PyForge Steward`), since the
element profile marks `title` MUST NOT be slug-constrained
**And** `maintainer` and `inherits` are sequences (§6.2.1 "A writer MUST emit a
sequence"), with `owner:` collapsed into the registered `maintainer`
**And** the aliases `name`/`inherits` are KEPT — §6.2.1 requires them of a
Markdown writer; `title`/`composition` belong to the YAML/JSON encodings
**And** the preflight keys identity off `identifier`, reports a scalar
repeatable, and still resolves a `path-ref` parent
**Status:** done

## Epic 54: Foundry kernel regenerate (spec-foundry-regenerate-not-fold fnr:CAP-1..145 / fnd:CAP-11)

Minted 2026-09-13 from `docs/dreams/foundry-regenerate-not-fold.md`. Operator
accepted regenerate-not-fold, A + thin oracle, Launch = CLI + MCP, CFE
rebuild-not-move, and **fnr:CAP-5** (Dream+Frame+Spec shared; A/B behavior;
BMAD-on-B clean). CAP-2..4 land in a **python-foundry** worktree. 54.5 lands
the A/B protocol on B (docs). Does not dispatch 44.4, 44.5, or 44.6. Does
not flip any Epic 44 `blocked` key. Does not flip `pyforge.cutover_root`.
Public CLI verbs stay.

### Story 54.1: Thin oracle for the foundry kernel

As a platform operator,
I want a frozen list of existing core, steward, and marshal tests that the
foundry kernel must pass,
So that regenerate is gated by behavior, not Frame frontmatter.

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** spec-foundry-regenerate-not-fold
CAP-1; fnd:CAP-11
**Surface:** tracked list under
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/`
(about 20–40 tests: CLI, exit codes, `station_port`, cutover-root reader,
no-host). Implementation of the packages is 54.2–54.4.
**Given** Frame preflight is schema-only **When** this story lands **Then** a
named archived-test list exists and is the kernel gate
**And** the list cites existing tests in local-recipes; it does not wait for
44.14
**And** 44.4 / 44.5 remain undispatched
**Status:** done

### Story 54.2: Rebuild pyforge-core in foundry

As a platform operator,
I want `pyforge-core` born under foundry `src/packages/` from the port /
hooks / cutover-root contracts,
So that later stations have a leaf that was not folded from
`src/shared/packages/`.

**Type:** feature • **Effort:** M • **Deps:** S-54.1 • **FR/AD:** spec-foundry-regenerate-not-fold
CAP-2; fnd:CAP-11
**Note:** Commits go to `rxm7706/python-foundry`. Planning stays here.
**Given** CAP-1 list exists **When** this story lands **Then** foundry has a
core leaf whose CAP-1 core slice is green
**And** no `apply --phase 1a` copy of `pyforge-core` is the source
**Status:** done

### Story 54.3: Rebuild steward in foundry

As a platform operator,
I want `pyforge steward` regenerated in foundry with CLI and MCP
(provision, workspace, frames, guards, cutover, suite register path),
So that the lasting root can provision the suite without folding the
brownfield engine.

**Type:** feature • **Effort:** L • **Deps:** S-54.2 • **FR/AD:** spec-foundry-regenerate-not-fold
CAP-3; fnd:CAP-11
**Given** foundry core is green **When** this story lands **Then**
`pyforge steward` on a foundry checkout passes the CAP-1 steward slice
**And** public verb `pyforge steward` is unchanged
**Status:** done

### Story 54.4: Rebuild marshal in foundry

As a platform operator,
I want `pyforge marshal` regenerated in foundry with cursor-native
dispatch, CLI and MCP,
So that one foundry-remote dispatch proves the kernel.

**Type:** feature • **Effort:** L • **Deps:** S-54.3 • **FR/AD:** spec-foundry-regenerate-not-fold
CAP-4; fnd:CAP-11
**Given** foundry steward is green **When** this story lands **Then** one
marshal dispatch against the foundry remote plus the CAP-1 marshal slice
are green
**And** `MRS-DISP-*` corners not in the thin list stay on local-recipes
until 44.14
**And** `pyforge.cutover_root` is still `local-recipes`
**And** the CAP-1 marshal cases have an A/B row that is not `diverge` (`ab-sync.md`)
**Status:** done

### Story 54.5: A/B protocol and pin on foundry

As a platform operator,
I want the dual-root protocol, a SHA pin file, and a short case-list stub
on `python-foundry`,
So that a new builder treats B as the clean BMAD tree and A as control,
without copying A's comments.

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-foundry-regenerate-not-fold
CAP-5
**Note:** Implementation is a **python-foundry** PR: rewrite README/AGENTS
as greenfield; add `docs/foundry/PIN.md`; add the case-list stub. This
repo keeps the Spec companion. Do not rsync `_bmad-output`.
**Given** `ab-sync.md` exists on A **When** this story lands **Then** B
has `PIN.md` pointing at this Spec SHA, a case-list stub, and operator
docs that do not say "replay 44.4"
**And** A does not receive a copy of B's slim chain
**Status:** backlog

## Epic 55: Foundry capability ledger (spec-foundry-capability-ledger fcl:CAP-1..145)

Minted 2026-09-13 from `docs/dreams/foundry-capability-ledger.md`.
**Strangler fig:** facade is public CLI (+ later `cutover_root`); ledger
is the routing table. Not a long-lived B branch that mirrors A. Modes:
`rebuild` | `retire` | `A-only` (expiry) | `B-only`. No `move`. Inventory
is a CAP heading extract. Lands as one kit with **53.5** (v0.3 Frames)
and **54.1** (case-list). Does not flip 44.1.

### Story 55.1: Tracked capability ledger

As a platform operator,
I want every live capability classified in one tracked yaml,
So that PIN-as-oracle is a check, not a feeling.

**Type:** docs • **Effort:** M • **Deps:** S-54.1 • **FR/AD:** spec-foundry-capability-ledger
CAP-1
**Surface:** `docs/foundry/capability-ledger.yaml`; companion
`modes.md`.
**Given** live `CAP-N` extracts exist **When** this story lands **Then**
each extract has a mode row
**And** there is no `move` key
**And** 44.1 remains `blocked`
**Status:** done

### Story 55.2: Extract detector in detectors-ci

As a platform operator,
I want unclassified or undated rows to fail `detectors-ci`,
So that a new CAP cannot sit invisible after a pin bump.

**Type:** feature • **Effort:** M • **Deps:** S-55.1 • **FR/AD:** spec-foundry-capability-ledger
CAP-2
**Surface:** doctor gather in `detectors-ci`; companion `extract.md`.
**Given** a fixture SPEC with a unique Why sentence and a `CAP-9`
**When** the detector runs **Then** it sees `CAP-9` and does not see
the Why sentence
**And** unclassified `CAP-N` is HARD
**And** `A-only` without expiry is HARD
**And** a path/Spec after the PIN SHA without a row is `--append`
**Status:** done

### Story 55.3: verified-in-foundry joins the case list

As a platform operator,
I want a `verified-in-foundry` claim to name a case-list id,
So that Frame preflight cannot stand in for A/B behavior.

**Type:** docs • **Effort:** S • **Deps:** S-55.1 • **FR/AD:** spec-foundry-capability-ledger
CAP-3
**Given** a ledger row claims `verified-in-foundry` without a 54.1
case-list id **When** the detector runs **Then** the finding is HARD
**And** a row that cites a listed id is not HARD for this reason
**Status:** done

## Epic 56: platform-dev boots the local leaf (spec-platform-dev-boots-local pdl:CAP-1)

Minted 2026-09-13 from `docs/dreams/platform-dev-boots-local.md`.
pap:AD-16 names `platform-dev` as the containerless local baseline.
`config.settings.local` always loads `debug_toolbar`; that package
was only on `platform-ci-test`. Image feature stays clean.

### Story 56.1: django-debug-toolbar on platform-dev only

As a platform operator,
I want `platform-dev` to load `config.settings.local`,
So that mint and `manage.py` do not require a second pixi env.

**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-platform-dev-boots-local
CAP-1
**Surface:** `pixi.toml` `[feature.platform-dev.dependencies]`;
`pixi.lock`; `src/platform/tests/policy/test_platform_dev_local_leaf.py`.
**Given** `platform-dev` python cannot import `debug_toolbar`
**When** `django-debug-toolbar` is pinned on the `platform-dev` feature
at the same floor as `platform-ci-test` (`>=8.0.0`)
**Then** that env imports `debug_toolbar` and can `django.setup()` under
`DJANGO_SETTINGS_MODULE=config.settings.local`
**And** `[feature.python-agent-platform]` does not declare the package
**And** a policy test fails if either pin is wrong
**And** the proof does not use Docker or CRC
**Status:** done

## Epic 57: One pixi env for the platform image (spec-platform-image-one-pixi-env)

**Retroactive.** All three CAPs shipped `59083b8391` (2026-08-25, "Fold the
platform image onto one python-agent-platform env") and were re-verified live
2026-09-11 (SPEC.md's own dated verification notes), but no story was ever
written, so `chain-completeness` flagged the Spec as undecomposed despite the
code being real, tested, and running. This epic documents what already
exists; no new implementation. Surface: `src/platform/Containerfile`,
`pixi.toml`/`pixi.lock`, `scripts/platform_image_pip_layer.py`,
`tests/packaging/test_platform_image_one_pixi_env.py` (repo-root `tests/`,
not `src/platform/tests/`).

### Story 57.1: One frozen env replaces the pip `--no-deps` layer

As a platform operator,
I want the platform image produced from a single `pixi install --frozen -e
python-agent-platform` whose lock already carries the Django-host extras,
So that a conda/pip overlap (the `mcp` package uninstall CRC hit 2026-08-25)
fails at lock time, never as a silent Containerfile uninstall.

**Type:** chore • **Effort:** M • **Deps:** — • **FR/AD:** spec-platform-image-one-pixi-env CAP-1
**Given** the extras lived in `[feature.platform-image-pip]` behind a `pip
install --no-deps` Containerfile RUN
**When** this story lands **Then** those extras (`django-structlog`,
`uvicorn-worker`, etc.) are pinned on `[feature.python-agent-platform.dependencies]`
directly from conda-forge
**And** the image interpreter imports them with no pip layer RUN
**And** `platform-ci-test` stays its own separate conda solve (psycopg3 vs image psycopg2)
**Status:** done — shipped `59083b8391` (2026-08-25); re-verified live
2026-09-11 (`import django_structlog` succeeds, no pip layer)

### Story 57.2: Containerfile drops the pip installer entirely

As a platform operator,
I want `[feature.platform-image-pip]` and `scripts/platform_image_pip_layer.py`
retired to a tombstone that fails loudly if resurrected,
So that the runtime image never runs a second, overlap-blind installer.

**Type:** chore • **Effort:** S • **Deps:** S-57.1 • **FR/AD:** spec-platform-image-one-pixi-env CAP-2
**Given** the Containerfile ran `python3 -m pip install --no-deps` for host extras
**When** this story lands **Then** `rg 'pip install --no-deps'
src/platform/Containerfile` is empty and `platform_image_pip_layer.py` exits
2 with "retired" in its stderr if invoked
**And** the 16.1 emitter is unused by the Containerfile
**And** `tests/packaging/test_platform_image_one_pixi_env.py` covers both claims
**Status:** done — shipped `59083b8391` (2026-08-25); re-verified live
2026-09-11 and again 2026-09-14 (3/3 `tests/packaging/test_platform_image_one_pixi_env.py` pass)

### Story 57.3: pixitainer-docker re-evaluated, hand-rolled Containerfile kept

As a platform operator,
I want the Docker/Podman pixitainer backend re-tested against the Story 10.3
contract now that it's on conda-forge,
So that adopting a generated Containerfile is a measured choice, not a retry
of the SIF-only rejection from 10.3.

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-platform-image-one-pixi-env CAP-3
**Given** `pixitainer-docker` 0.8.3 is now on conda-forge (missing as a Docker
backend when Story 10.3 evaluated SIF-only `pixitainer`)
**When** this story lands **Then** `pixitainer-eval.md` carries a dated Design
Note with each Story-10.3 must-hold row scored pass/fail and the CLI/package
actually invoked
**And** a failing row keeps the hand-rolled Containerfile rather than
reopening SIF-only `pixi-containerize`
**And** Mason presenton's own pixitainer usage is untouched either way
**Status:** done — shipped `59083b8391` (2026-08-25); Design Note recorded
outcome: fail, hand-rolled Containerfile kept

## Epic 58: The mcp-host sidecar hosts real station tools (spec-mcp-host-real-station-tools)

**Retroactive.** All three CAPs shipped `20a85dcc79` (2026-09-12, "mcp-host sidecar
hosts marshal's real MCP tools") and each carries its own dated `shipped:` proof
line in the Spec, but no story was ever written, so `chain-completeness`'s new
delivered-Spec arm flagged the Spec as undecomposed despite the code being real,
deployed, and proven live on CRC. This epic documents what already exists; no new
implementation. Additive to `spec-mcp-era-isolation`'s shipped slices 1-3, which
are held exactly as they were.

### Story 58.1: A station's real MCP tool is reachable through a deployed cluster

As a platform operator,
I want an agent calling `/stations/<name>/mcp` to reach that station's real tool
implementation, not the identity stub,
So that a correctly-signed host assertion can publish a run against a deployed
cluster instead of being answered with `Unknown tool`.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-mcp-host-real-station-tools CAP-1
**Surface:** `src/platform/mcp_host/app.py`; `src/platform/mcp_host/settings.py` (minimal
Django settings — `django_pyforge` + `django_marshal_portal` only, no Langflow, no Redis);
`src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py`
**Given** `asgi_for_station(name)` registered exactly one tool, `station_face()`, returning
the station's own name **When** this story lands **Then** the sidecar discovers marshal's
real held-loop tools through the same `iter_station_mcp_apps()` seam the web pod uses
in-process
**And** `POST /stations/marshal/mcp` with `publish_loop_run` returns a run handle from
`publish_held_loop_bounded`, never `Unknown tool: publish_loop_run`
**And** the MCP SDK's `**payload: Any` → required-nested-`payload` schema bug the first fix
uncovered is fixed in the same pass
**Status:** done — shipped `20a85dcc79` (2026-09-12); proven live against the deployed CRC
cluster: a real `HostPublisher` published, heartbeat'd and completed a run

### Story 58.2: A station with no real app keeps the slice-1 stub, unchanged

As a platform operator,
I want every station without a real in-process MCP app to keep answering exactly as
slice 1 shipped it,
So that adding real-tool hosting for one station cannot regress the other eight.

**Type:** feature • **Effort:** S • **Deps:** S-58.1 • **FR/AD:** spec-mcp-host-real-station-tools CAP-2
**Given** only marshal has a real app **When** this story lands **Then**
`spec-mcp-era-isolation`'s CAP-1..145 acceptance (dual-era handshake, protocol-version
negotiation, 405 on non-POST) still holds unchanged for every station without one
**And** `_apps` covers all 9 default stations while `_real_apps` covers only `{"marshal"}`
**And** a `django.setup()` failure for any reason falls back to the stub for **every**
station, covered directly by a mocked-failure unit test on that isolation seam
**Status:** done — shipped `20a85dcc79` (2026-09-12); sidecar boot logs show all 9 session
managers starting cleanly

### Story 58.3: The one unproven run-state row flips to PASS

As a platform operator,
I want `spec-run-state-one-publisher`'s last unproven verification row closed,
So that "live run appears on `/runs/`, timing survives teardown" is evidence, not intent.

**Type:** chore • **Effort:** S • **Deps:** S-58.1 • **FR/AD:** spec-mcp-host-real-station-tools CAP-3
**Surface:** chart `mcp-host` Deployment gains the DB/secret env it needs plus postgres
egress/ingress (previously DNS-only)
**Given** that row read `NOT PROVEN` because the real tool was never registered on the
server answering the call **When** this story lands **Then**
`spec-run-state-one-publisher/verification-2026-09-12.md` records it `PASS` with the live
run's evidence
**And** the run's timing is queryable after the workstation that drove it is gone
**Status:** done — shipped `20a85dcc79` (2026-09-12)

## Epic 59: One name, one job (spec-vocabulary-one-name-one-job CAP-1..145)

Minted 2026-09-15 from `docs/dreams/vocabulary-one-name-one-job.md` after the
operator accepted Q1–20. Spec `ready`. **CAP-4** (`Track` / `Gate`) is already
met — no story. Herald executes the deck half of CAP-5; doctor sources consume
CAP-2; atlas owns CAP-8's six `check=` sites. Do not flip any Epic 44 `blocked`
key. Do not retro-rename existing slugs or `DW-` ids.

### Story 59.1: The Spec ladder is declared and the Charter states the rule

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-vocabulary-one-name-one-job CAP-1
**Surface:** `docs/governance/`; `docs/dreams/pyforge-charter.md`;
`docs/dreams/README.md` stays the Dream ladder only.
**Given** eight Spec statuses are live and only `extension-point` is defined
**When** this story lands
**Then** all eight are defined, the three ended-acts are not collapsed, and
`shipped` remains Spec-terminal
**And** the enum is recommended, not required; unknown values are preserved
and warned, never reset
**Status:** backlog

### Story 59.2: Detectors read one declaration; in-progress is grandfathered

**Type:** feature • **Effort:** M • **Deps:** S-59.1 • **FR/AD:** spec-vocabulary-one-name-one-job CAP-2
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py`,
`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py`,
`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py`,
exit-code domains named in the same declaration file (different key;
`DW-VOCAB-2026-09-14-8`).
**Given** those modules each keep a private status set
**When** this story lands
**Then** they import the CAP-1 declaration
**And** new Specs are not written `in-progress`; live `in-progress` files stay
open until next edited
**And** Doctor⊂Warden remains a declared subset
**Status:** backlog

### Story 59.3: The Charter carries the BMAD cross-walk and pitched stays optional

**Type:** docs • **Effort:** S • **Deps:** S-59.1 • **FR/AD:** spec-vocabulary-one-name-one-job CAP-3
**Surface:** `docs/dreams/pyforge-charter.md`; `docs/governance/guild-roster.json`.
**Given** Hub has a Charter walk and BMAD's daily nouns do not
**When** this story lands
**Then** the Charter maps Epic / Story / Sprint / PRD / Retrospective (never
join) and records Spec `shipped` ≠ story `done` ≠ Dream `realized`
**And** `pitched` remains declared and optional; no Dream is backfilled
**Status:** backlog

### Story 59.4: Design teaching is named; the pull cannot silently rot

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-vocabulary-one-name-one-job CAP-5
**Surface:** `presentations/agentic-sdlc/`; `DW-VOCAB-2026-09-14-3`.
Herald executes the pull; steward wrote the ruling.
**Given** the deck teaches four-phases / three-tracks and is 13.5 KB behind
**When** this story lands
**Then** the deck names itself teaching-only (except method-vs-machinery and
project-context-as-constitution)
**And** retired BMAD skill names and Paige are gone from the pulled deck
**And** a detector flags a silent size/etag drift
**And** the pulled deck does not label story modes L1–L5 or an autonomy
percentage (operator 2026-09-16: teaching-only until the Guildhall exists)
**Status:** backlog

### Story 59.5: One mint-time slugify and two DW families

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-vocabulary-one-name-one-job CAP-6
**Surface:** `scripts/deferred_work_promote.py`
**Given** one story is spelled three non-derivable ways and `DW-` has eleven grammars
**When** this story lands
**Then** a new story's heading, ledger key, and `spec-<ledger-key>.md` derive
from one function
**And** a new `DW-` id is story-scoped or sweep-scoped and includes the short
station token
**And** the 53 divergent slugs and 1338 existing `DW-` ids are untouched
**Status:** backlog

### Story 59.6: Shape hygiene — roster, S-N.N, commits, status comments

**Type:** feature • **Effort:** M • **Deps:** S-59.1 • **FR/AD:** spec-vocabulary-one-name-one-job CAP-7
**Surface:** `docs/governance/guild-roster.json`; Dream files under `docs/dreams/`;
commit-subject convention (hook or detector). `S-N.N` stays prose-only.
**Given** four `STATIONS` lists disagree and 19 Dreams comment on `status:`
**When** this story lands
**Then** one roster of eight exists (LONG paths/packages/envs, SHORT
`owner:` / `Source` / prose)
**And** a trailing `#` on Dream `status:` is a finding
**And** commit subjects are Capitalized sentences with no trailing period,
except `type(scope):` under `recipes/` and the CFE changelog
**Status:** backlog

### Story 59.7: atlas check= is a finding code only

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-vocabulary-one-name-one-job CAP-8
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py`
**Given** six sites put runtime data in the finding-code field
**When** this story lands
**Then** those sites put the data in `evidence` and `check=` stays a kebab code
**Status:** backlog

## Epic 60: Estate BMAD catalog (spec-self-hosted-bmad-marketplace CAP-1..145)

Minted 2026-09-15 from `docs/dreams/self-hosted-bmad-marketplace.md` after the
operator approved Q1–7. Spec `ready`. **CAP-5** (Claude-skill source slot)
is an empty later slot — no story. **CAP-6** (Hub Layer 3) is a recorded
non-goal — no story. Do not flip any Epic 44 `blocked` key. Creating a new
GitHub catalog repo needs operator confirm at 60.1.

### Story 60.1: The catalog config names backends and sources

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-self-hosted-bmad-marketplace CAP-1
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-self-hosted-bmad-marketplace/backends-and-sources.md`;
a config the installer and Claude/Codex `extraKnownMarketplaces` can point at.
**Given** listings have no estate home and no named source
**When** this story lands
**Then** git is the edit store and backends/sources are declared in config
**And** a new backend or source is a plugin, not a rewrite
**Status:** backlog

### Story 60.2: Publish uses tools we wield; steward records the review

**Type:** feature • **Effort:** M • **Deps:** S-60.1 • **FR/AD:** spec-self-hosted-bmad-marketplace CAP-2
**Surface:** Builder / module-template / SKF publish path; the estate catalog
registry YAML.
**Given** a module can appear without a recorded review
**When** this story lands
**Then** a listing cannot appear without steward review, unless it is already
in the wielded suite (Certified)
**And** tiers are Unverified / Community Reviewed / BMad Certified
**Status:** backlog

### Story 60.3: Ship backends — conda channel default

**Type:** feature • **Effort:** M • **Deps:** S-60.1 • **FR/AD:** spec-self-hosted-bmad-marketplace CAP-3
**Surface:** a noarch catalog-index recipe under `recipes/`; the existing
SelfExplainML / Artifactory channel path.
**Given** an air-gapped host cannot install without github.com
**When** this story lands
**Then** the default ship path is a pixi/conda index package on that channel
**And** object storage and git bundle / tarball are switchable extras
**Status:** backlog

### Story 60.4: Frame index and a thin browse list

**Type:** feature • **Effort:** M • **Deps:** S-60.1 • **FR/AD:** spec-self-hosted-bmad-marketplace CAP-4 CAP-7
**Surface:** `docs/foundry/frames/`; a generated index or existing chrome page.
**Given** operators read YAML by hand and Frames have no catalog row
**When** this story lands
**Then** a read-only list shows modules and Frames (name, tier, link or
install hint)
**And** a Frame listing is a reviewed git add; share uses CAP-3 backends
**And** it is not an App Store, MyBMAD, Collab, or nebari-frames
**Status:** backlog

## Epic 61: Work passports and dated extracts (spec-work-passports-dated-extracts CAP-1..145)

Minted 2026-09-15 from `docs/dreams/work-passports-dated-extracts.md` after the
operator approved Q1–6. Spec `ready`. **CAP-6** and **CAP-7** (larva) are
empty later slots — no story. Do not treat Epic 8 as this product. Do not
flip any Epic 44 `blocked` key. Do not PAT into the vendor private GitHub.

### Story 61.1: Corridor transports — upload default

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-work-passports-dated-extracts CAP-1
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-work-passports-dated-extracts/transports-and-vendors.md`;
the existing Postgres app / a steward load duty.
**Given** vendor and estate lists have no idempotent drop path
**When** this story lands
**Then** inbound and outbound files load by batch sha + waybill
**And** default transport is app upload; email and share-folder are plugins
**Status:** backlog

### Story 61.2: Work passport and core schema

**Type:** feature • **Effort:** M • **Deps:** S-61.1 • **FR/AD:** spec-work-passports-dated-extracts CAP-2
**Surface:** the existing Postgres join store.
**Given** Jira keys and GitHub numbers can collide across rooms
**When** this story lands
**Then** identity is a UUID we mint; keys and numbers are nicknames
**And** `vendor_id` is on inbound rows; v1 operates one vendor
**Status:** backlog

### Story 61.3: As-of glass and mailed query

**Type:** feature • **Effort:** M • **Deps:** S-61.2 • **FR/AD:** spec-work-passports-dated-extracts CAP-3
**Surface:** existing app views `standup` and `shipped`; optional CSV/markdown export.
**Given** standup asks "any news from the vendor?"
**When** this story lands
**Then** standup cites a waybill; empty on-time file fails; late drop leaves yesterday stale; unborn before first waybill
**And** a mailed/export of the same table is a switchable plugin
**Status:** backlog

### Story 61.4: Signed outbound slice

**Type:** feature • **Effort:** M • **Deps:** S-61.2 • **FR/AD:** spec-work-passports-dated-extracts CAP-4
**Surface:** outbound loader; named `outbound-signer` role on the existing app.
**Given** a dump of Jira or factory BMAD can leave unsigned
**When** this story lands
**Then** default deny; a named slice plus recorded signer is required
**And** the vendor loads our file — we do not PAT into their org
**Status:** backlog

### Story 61.5: Quarantine — mint then reject

**Type:** feature • **Effort:** M • **Deps:** S-61.2 • **FR/AD:** spec-work-passports-dated-extracts CAP-5
**Surface:** quarantine shelf on the existing app.
**Given** inbound rows arrive without a passport
**When** this story lands
**Then** first 14 days (config) mint into quarantine; after that, no mint
**And** no title-match endpoint exists
**Status:** backlog

## Epic 62: Published measure catalog (spec-build-league-scorecard CAP-1..145)

Minted 2026-09-15 from `docs/dreams/build-league-scorecard.md` after the
operator approved the eight already-counted signals and required on/off/
archived config. Spec `ready`. **CAP-4** (dashboard / league table) is an
empty later slot — no story. Do not invent weights. Do not flip any Epic 44
`blocked` key.

### Story 62.1: The catalog names eight measures and their states

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-build-league-scorecard CAP-1
**Surface:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md`;
`docs/dreams/pyforge-unifying-strategy.md` Q5 cite.
**Given** Q5 named faces and no numbers
**When** this story lands
**Then** the eight ids are published with dimension, source, and state
**And** first cut is all `on`; no consumer invents a substitute
**Status:** backlog

### Story 62.2: Add, switch, and archive without a rewrite

**Type:** feature • **Effort:** M • **Deps:** S-62.1 • **FR/AD:** spec-build-league-scorecard CAP-2
**Surface:** a config the catalog and later consumers read.
**Given** a new source or a dead source would fork the product
**When** this story lands
**Then** add is a new row starting `off`; archive keeps the id and forbids reuse
**And** `on` / `off` / `archived` is a config flip
**Status:** backlog

### Story 62.3: Consumers cite `on` rows only

**Type:** feature • **Effort:** M • **Deps:** S-62.1 • **FR/AD:** spec-build-league-scorecard CAP-3
**Surface:** a refuse path Herald / Atlas / Marshal / Doctor can call.
**Given** a station can mint a stealth metric
**When** this story lands
**Then** citing `off`, `archived`, or an unknown id is a refuse
**And** Hub Outcome Guards are not implemented here — they read later
**Status:** backlog


## Epic 63: The Guild environment — `pyforge-guild` is the default for every agent (spec-pyforge-steward CAP-5)

Minted 2026-09-16 Dream-append-first from `docs/dreams/pyforge-steward.md` § *2026-09-16 — The
Guild environment* (no new Dream file, no satellite Spec; `spec-one-chain-per-station` CAP-1).
Operator ruling: `local-recipes` (222 conda deps, 171 tasks, 10 GB) predates the Guild and is the
wrong default for pixi.toml, for Claude/Cursor/Copilot/Gemini and for Cursor Cloud Agents in
RXM-LOCAL-RECIPES. Measured at `41e29805b5`: 48 of its 171 tasks are Guild/planning work whose
scripts import only `pyforge.*`, `yaml`, `tomli`, `pixi_version_registry`; 86 are recipe-factory
(Mason's). **Tasks move, never duplicate** (Spec Constraint CAP-5). `local-recipes` keeps its name
and every task by *including* the new feature. Foundry mode `rebuild`. Do not touch `recipes/`; do
not invoke `conda-forge-expert`. `pixi.toml` changes: regenerate `environment.yaml` in the same PR
and run `pyforge-station-tests` (shared surface, all eight fire in CI).

### Story 63.1: The `pyforge-guild` feature and environment exist and the Guild tasks live in it

**Type:** infra • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-5
**Surface:** `pixi.toml` (`[feature.pyforge-guild]`, `[environments]`, the 48 moved `[feature.pyforge-guild.tasks.*]`), `pixi.lock`, `environment.yaml`, `scripts/detectors.py` if it names an env.
**Given** every planning task is reachable only through a 10 GB environment
**When** this story lands
**Then** `pixi install -e pyforge-guild` from cold is under 1 GB on disk and `pixi run -e pyforge-guild detectors-ci` is green on `main`
**And** every moved task still runs as `pixi run -e local-recipes <task>` because `local-recipes` includes `pyforge-guild`; no task name exists in two features
**And** `pyforge-station-tests` and `pr-preflight` pass from `pyforge-guild`; `environment.yaml` is regenerated
**And** the token-economy kit is on the floor, not assumed: `headroom` and `node` resolve on PATH in `pyforge-guild`, `marshal seed check` reports the headroom kit item present, and a dispatch dry-run raises no `MRS-DISP-033` (the 2026-09-01 silent no-op shape)
**Status:** backlog

### Story 63.2: Every agent surface names `pyforge-guild` as the session default

**Type:** docs • **Effort:** S • **Deps:** S-63.1 • **FR/AD:** spec-pyforge-steward CAP-5
**Surface:** `AGENTS.md` (`bmad:context` block via `bmad-project-context`), `CLAUDE.md`, `.cursor/rules/*.mdc`, `.claude/skills/pyforge-*/SKILL.md`, `.cursor/one-chain-folds/README.md` briefs, the Cursor cloud-environment install command, `docs/reference/library-llms-full.md` env-membership rows (`llms-full-check` green).
**Given** every document tells an agent `pixi run -e local-recipes …` for planning work
**When** this story lands
**Then** the planning/detector invocations read `-e pyforge-guild`; recipe invocations still read `-e local-recipes`; scribe recall still reads `-e pyforge-scribe`
**And** `governance-currency`, `general-docs-consistency-check` and `llms-full-check` are green
**Status:** backlog

### Story 63.3: One deny list, one hook — the Guild session guardrails are enforced, not asserted

**Type:** feature • **Effort:** M • **Deps:** S-63.1 • **FR/AD:** spec-pyforge-steward CAP-5; marshal-token-economy:CAP-20 (silent saves; the front door)
**Surface:** `docs/governance/guild-roster.json` (a new closed `session_denials` list, the ONE declared source), `.claude/hooks/pre-shell.py` (new; registered `PreToolUse` on `Bash` and on `Edit`/`Write` in `.claude/settings.json`, `permissionDecision: deny` + reason), `.cursor/hooks.json` (new, force-tracked; `beforeShellExecution` deny — Cursor has no before-edit deny, so file rules there are `afterFileEdit` warn), tests under `tests/` for the script (the hook is repo-level, not a station package).
**Given** an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo
**When** the command or path matches a `session_denials` entry: `pixi run -e local-recipes <guild task>` (the `guild-tasks` set read from `pixi.toml`, never a copy); `pip install` / `uv pip install` / `conda install` / `npx <x>` except `npx skills add`; `pixi add` / `pixi update`; `scripts/bmad-switch` when a worktree or `BMAD_ACTIVE_PROJECT` is present; `git commit` on `main` or in the primary checkout, or with `Co-Authored-By` / AI attribution; `gh pr merge --squash`; `gh pr create` without `--repo rxm7706/local-recipes`; `uv run` with cwd ≠ repo root; `spec_surface_check.py --write-baseline` without `--spec`; a direct write to `SPEC.md`, `sprint-status-ledger.yaml`, or a tracked path under `implementation-artifacts/`
**Then** the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never denies anything not on the list (the list is closed; adding to it is a governance act on `guild-roster.json`)
**And** the same script serves both harnesses; harnesses without a verified deny surface (Gemini CLI, Copilot CLI, Devin) are named as instruction-only in `AGENTS.md`, not silently assumed covered
**Status:** backlog

### Story 63.4: `steward session check` — one verdict for the session preconditions, run from every entry point

**Type:** feature • **Effort:** M • **Deps:** S-63.1, S-63.3 • **FR/AD:** spec-pyforge-steward CAP-5; AD-8 (`DutyResult` is frozen evidence; duties never `sys.exit`)
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/` (new `session` duty, `pyforge steward session check`, exit domain `0` ok / `1` findings / `70` crash), `.claude/hooks/session-start.sh`, `.cursor/environment.json` (`start`), `.github/workflows/copilot-setup-steps.yml`, the Marshal dispatch preamble (`pyforge-marshal` calls the steward CLI, never imports it), station tests.
**Given** a session begins on any harness, local or cloud
**When** `pyforge steward session check` runs
**Then** it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token kit — `headroom` on PATH, this harness's caveman skill installed, the three context layers not `layer-off` (reuse `marshal seed check`); `gh auth status` and `gh api rate_limit` (an unauthenticated session is a finding, because drift probes fail open); the codegraph index present (absent in every fresh clone); **the Tier-3 feed present for the project in hand — and when absent, the one sanctioned remedy: seed it by copying the tracked twin (`cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml`; verified 2026-09-16 in a fresh clone: `sprint-ledger-sync` then reports `unchanged`, tree clean)**; scribe recall reachability (absent by design in `pyforge-guild` — reported, not failed)
**And** the four entry points call this one command and nothing else for preconditions (vocabulary-one-name-one-job: one mechanism, many surfaces); a cloud clone with no feed can land a ledger flip by following the printed remedy
**Status:** backlog

## Epic 64: Frame draft re-grounding at frame-spec#28 `d7213c1` / #29 `4596579` (spec-pyforge-steward CAP-6)

Minted 2026-09-16 Dream-append-first from `docs/dreams/pyforge-steward.md` § *2026-09-16 — Frame
draft re-grounding*; Frames remain `spec-intelligence-hub` CAP-2's subject (Epic 53 shipped the
adoption 09-13/14). What changed upstream since our grounding, measured read-only: #28's 09-14
commit removes the draft's version number (examples read bare `type: frame`); #29 (81 commits)
adds the reference validator, composition fixtures, `--self-check`, and conformance profiles,
which §7 makes a MUST for every implementation. Upstream's own `validate_frame.py` at #29's head
passes our nine Frames 9/9. **No commits or comments to openteams-ai repositories** — the
validator is fetched to a temp dir at a pinned SHA, never vendored. Not a gate: `frame-preflight`
and `frame-upstream-check` never join `detectors-ci`; Warden stays the sole PR verdict.

### Story 64.1: The nine Frames go bare `type: frame` and the README pins the upstream heads

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-6 (a), (b), (c)
**Surface:** `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/*.frame.md`, `docs/foundry/frames/README.md` (Upstream pin block), `src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py` docstring, `pixi.toml` `[feature.pyforge-steward.tasks.frame-upstream-check]`, deferred-work ledger accepted-risk entry.
**Given** our Frames stamp `frame [0.3]`, a version no release has assigned
**When** this story lands
**Then** all nine read `type: frame`; `frame-preflight` is green; the README names the #28 and #29 SHAs we conform to
**And** `pixi run -e pyforge-steward frame-upstream-check` clones frame-spec at the pinned SHA into a temp dir and reports 9/9 OK, exiting non-zero on any FAIL; it is opt-in and appears in no aggregate
**Status:** backlog

### Story 64.2: PyForge publishes its Frame conformance profile

**Type:** docs • **Effort:** S • **Deps:** S-64.1 • **FR/AD:** spec-pyforge-steward CAP-6 (d); Constraint CAP-6
**Surface:** `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/README.md` § Conformance profile.
**Given** §7 requires every implementation to publish a profile and PyForge has none
**When** this story lands
**Then** the profile states all ten §7 items for the in-repo reader (reads Markdown, writes none, resolves no composition, `visibility` is declared intent, `specification: draft-mcandrew-frame-spec-00`) and declares under §9 that no trust configuration exists yet
**And** upstream `validate_frame.py --check-profile` at the pinned SHA accepts it via `frame-upstream-check`
**Status:** backlog

## Epic 65: The estate sprint-ledger query engine (spec-pyforge-steward CAP-146..149; partially CAP-140)

Minted 2026-09-19 at the review of PR #1507 (a parallel session): the session had appended this as Story 63.5 under
Epic 63 "The Guild environment", which it has nothing to do with, under a standalone Dream + Spec carrying
`fold-exemption: cross-station-seam`. Folded per one-chain-per-station: the seed is the 2026-09-19 entry on
`docs/dreams/pyforge-steward.md`, the contract is `spec-pyforge-steward` CAP-146..149, the passport slice binds to
CAP-140 with Story 61.2 still the story of record. The `63-5` key never reached `main`; re-minted here as 65.1.
**HARD boundaries:** steward exports, Atlas renders (canopy:AD-13 / canopy:AD-23); no default write into another station's
tree; the minted UUID is identity; TRACKED ledgers only and `fleet_scan.parse_sprint_status` stays the reader of
record; stdout carries payload only.

### Story 65.1: Reusable, pluggable, feature-flagged estate sprint ledger query module & BMAD skill

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-146, CAP-147, CAP-148, CAP-149 (folded from spec-sprint-ledger-query-module 2026-09-19) • partially realizes CAP-140 (Story 61.2 remains the story of record)
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py`, `.../steward/dashboard/models.py` (`WorkPassport`), `.../steward/dashboard/admin.py`, `.../steward/dashboard/views_htmx.py`, `.../steward/dashboard/passport_sync.py`, `.../steward/dashboard/migrations/0002_workpassport.py`, `.../steward/cli.py` (`ledger-query` duty), `.../steward/data/sprint-ledger-query.schema.json`, tests (`test_sprint_ledger_query.py`, `test_dashboard_admin_and_htmx.py`, `test_cli.py`, `test_restore_duty.py`, `tests/meta/test_invariants.py`), `pixi.toml` (two tasks), `.claude/skills/bmad-sprint-ledger-query/SKILL.md`, `AGENTS.md` (pre-PR checklist). Surface paths corrected at review 2026-09-19 (the mint named `steward/models.py` etc. at paths that do not exist).
**Given** estate sprint ledgers are scattered across stations and lack pluggable querying, Work Passport UUID identity, and multi-system output formatters
**When** this story lands
**Then** `SprintLedgerQueryEngine` provides a pluggable engine with feature-flag evaluation (OpenFeature-shaped `eval_flag`: CLI `--flag` → `FLAGS_<NAME>` env → `.steward/flags.json` → default; no SDK), Work Passports PostgreSQL sync with minted UUIDs, multi-format output (markdown, summary, json, table, sync-matrix, herald-facts, atlas-dataset, static-dossier, jira-csv, github-json), HTMX dashboard view, Django Admin registration, CLI verb `pyforge steward ledger-query`, Pixi tasks `sprint-ledger-query` (`pyforge-guild`) and `sprint-ledger-postgres-sync` (`pyforge-steward`), and the `bmad-sprint-ledger-query` skill
**Outcome (2026-09-19):** landed as PR #1507 after review + remediation (three review layers; deps grammar, epic status,
flags wired, stdout purity, HTML escaping, read-only audit admin, Postgres sync refusing instead of no-op'ing, the
`--epic` filter CAP-146 names, the sync task moved to the env that has django); tracked spec
`specs/spec-65-1-reusable-pluggable-feature-flagged-estate-sprint-ledger-query-module-and-bmad-skill.md` carries
the triage log and Auto Run Result; CAP-146..149 shipped, CAP-140 partially realized.

### Story 65.2: The ledger query answers done / running / next in one call

As a fleet operator asking what is completed, running and queued next by station,
I want every story the query engine returns to carry a `next` field, with `--ready` / `--running` filters and per-station ready/running counts in the summary,
So that `sprint-ledger-query -- --unimplemented --format table` is the one command, instead of `fleet-picture` + `sprint-ledger-query` + `marshal watch` + a hand-written join.

**Type:** feature • **Effort:** S • **Deps:** S-65.1 • **FR/AD:** spec-pyforge-steward CAP-150 • operator ask 2026-09-20 08:00Z; re-opens Epic 65 (operator's choice over a new epic)
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` (`next` on the story item — `done` / `running` / `ready` /
`waits on S-x.y[, …]` / `blocked` / `?`; `--ready`, `--running` on the existing `ledger-query` duty — no new duty, duty-count invariants
unchanged; the running fact from `marshal watch --fleet --format json` via `pyforge.core.process`, one call per query, fail-open to `?` +
one WARN; summary counts; table/markdown/json columns), `.claude/skills/bmad-sprint-ledger-query/SKILL.md` (Quick Invocations gain `--ready` / `--running` and the `next` column — every documented
invocation runs verbatim, CAP-149), `docs/how-to/monitor-the-fleet.md` (the one-command answer, with `sources:` naming the module and the skill —
doctor Story 30.1's authored-page convention), `tests/unit/test_sprint_ledger_query.py` (fixture: the 2026-09-20 08:00Z ledgers/epics + a recorded watch payload; the unreachable-marshal case).
**Given** at 2026-09-20 08:00Z the answer to "what is done, running and next, by station" took three commands and a hand-written script, though
65.1 already ships the ready predicate as `get_runnable_backlog()`
**When** the engine annotates every story with `next`, reads the running fact from marshal's own CLI, and the duty gains `--ready` / `--running`
**Then** the fixture query reproduces that view verbatim (doctor 29.1 running; 24.1, 30.2 ready; 24.2, 24.3, 30.3 waiting; marshal 46.7 running;
46.1, 46.2, 46.6, 46.9, 46.10, 47.1 ready; steward 61.4 running; 61.5, 59.3–59.7, 60.2–60.4, 62.2, 62.3, 63.3 ready), `--ready` equals
`get_runnable_backlog()`, and `--running` equals the watch payload's running rows
**And** steward never imports `pyforge.marshal` or parses its journal; with marshal unreachable `next` reads `?` with one WARN and the exit code is
unchanged; the per-clone scope of the running fact is stated in `--help`, in the skill and in the how-to
