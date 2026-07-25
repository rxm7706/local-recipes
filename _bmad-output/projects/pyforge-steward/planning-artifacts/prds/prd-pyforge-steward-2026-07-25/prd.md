---
title: Steward (pyforge-steward)
created: 2026-07-25
updated: 2026-07-25
status: final
---

# PRD: Steward (`pyforge-steward`)
*Working title — confirmed against `docs/dreams/pyforge-steward.md`; not expected to change.*

## 0. Document Purpose

This PRD is for whoever runs `bmad-architecture` and `bmad-create-epics-and-stories` next, and for the future session (human or bmad-loop) that implements Steward's stories. It builds directly on `_bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md` (product framing, non-goals, success criteria) and the two 2026-07-25 research reports under `planning-artifacts/research/` (comparable-tool landscape, packaging precedent) — it does not re-derive that grounding, only cites it. Vocabulary is Glossary-anchored (§3); functional requirements are grouped by feature/duty and numbered globally (FR-1 through FR-18) so downstream epics/stories can reference stable IDs. Every open question the brief carried forward has been given an explicit decision in this PRD (§8 records confidence level per decision) rather than re-deferred.

## 1. Vision

Steward is the CLI (`steward`, package `pyforge-steward`, module `pyforge.steward`) that owns the pyforge ecosystem's platform/deployment/operations station: provisioning the environments the factory runs on, deploying the services it ships, holding the keys that guard it, and enforcing the budget ceilings that bound it. It exists to close a gap this repo has already paid for twice — a leaking JFrog API key and a committed Anthropic API key that needed history rewritten — by turning "no privilege outlives its deployment" from a motto into a property the codebase can be tested against. Steward is not a new platform; it is a thin, argparse-based CLI (matching its packaging sibling `pyforge-warden`) that wraps and formalizes tools and processes that already exist in this repo — `_http.py`'s credential-routing chokepoint, the hand-run `dashboard-gen` + push loop, the 14-environment pixi estate, and a currently-unenforced "$1500/month" budget doctrine.

## 2. Target User

### 2.1 Jobs To Be Done

- As the sole maintainer/operator of this factory, I need every credential I issue to have a bounded scope and a bounded life, so a leak like `JFROG_API_KEY`'s cross-host injection can't recur silently.
- As the same operator, I need to stop hand-running `dashboard-gen` + `git push` and trust a single command did the right, idempotent thing.
- As the same operator (or an unattended bmad-loop session acting on my behalf), I need to materialize any of the pixi estate's ~14 environments without recalling the exact `pixi install -e <name>` invocation or which feature composes it.
- As the same operator, I need the "$1500/month locked" doctrine to be something I can query and eventually check machine-readably, not just a sentence in a Dream file.

### 2.2 Non-Users (v1)

There is no external customer and no second human operator. Steward is not designed for a multi-tenant team, a paying customer, or a general-audience open-source user in v1 — it is dogfooded tooling for this repo's own maintainer, acting through every other pyforge Crew persona and every bmad-loop session. Multi-operator/team features are out of scope (§5).

### 2.3 Key User Journeys

*Downscaled per the template's guidance for internal tooling with a single operator role — each duty gets a one-sentence journey rather than a full multi-beat narrative.*

- **UJ-1.** The operator, having just read a Doctor-class finding about a credential leak, runs `steward keys audit --drift` and gets a report naming the exact code path that needs host-scoping, then fixes it and reruns to confirm clean. Realizes FR-4, FR-7.
- **UJ-2.** The operator, having edited `docs/dashboard/generate.py`, runs `steward deploy dashboard` once and trusts that nothing happens if there's no real diff, and a clean reconciled commit+push happens if there is. Realizes FR-8–FR-11.
- **UJ-3.** A bmad-loop session, needing the `pyforge-atlas` environment for a new worktree, runs `steward provision --env pyforge-atlas` instead of recalling the raw `pixi install -e` invocation. Realizes FR-12, FR-13.
- **UJ-4.** The operator, six months from now, runs `steward budget show` to remember what ceiling was declared and when, instead of grepping Dream files. Realizes FR-16, FR-17.

## 3. Glossary

- **Duty** — one of Steward's four independently-shippable responsibility areas: keys, deploy, provision, budget. Each duty is an engine module behind a shared interface (mirrors `pyforge-warden`'s `interfaces.py` pattern).
- **Host-scoped credential** — a credential whose attachment to an outbound HTTP request is gated by the request's destination host, not attached unconditionally (the fix-shape for the `JFROG_API_KEY` leak pattern).
- **Reconciliation** — a deploy step that diffs current-vs-desired state and only acts (commits/pushes) when a real difference exists, rather than blindly re-applying every run.
- **Ceiling** — a machine-readable declared resource-spend limit (e.g. `1500usd/month`), distinct from *enforcement* (checking live spend against the ceiling), which v1 does not implement.
- **pixi environment estate** — the named entries in this repo's root `pixi.toml` `[environments]` table (currently ~14: `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`, `pyforge-warden`, `pyforge-atlas`, `bmad-ui`, and combinations).
- **Age identity / recipient** — the private/public keypair pair used by the `age` encryption tool; Steward's `keys` duty uses these as its at-rest secret-encryption primitive (§4.1, decision D2).

## 4. Features

### 4.1 Keys

**Description:** Credential issuance, scoping, rotation, and revocation, closing the exact gap named in the Dream as Steward's "first case on the desk." Wraps `_http.py`'s existing host-scoped/`skip_auth` routing rather than reimplementing it, and uses `age` for Git-native at-rest secret encryption (Decision D2, §8 — no standing secrets-manager service). Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Host-scoped credential resolution

`steward keys` provides a resolver that any Steward-issued or Steward-audited credential attachment goes through, gating attachment by the request's destination host — equivalent in spirit to `_http.py`'s `skip_auth=True` guard.

**Consequences (testable):**
- A credential declared with an explicit host allowlist is never attached to a request outside that allowlist, verified by a unit test constructing an out-of-allowlist URL.
- The resolver is a thin wrapper importing/delegating to `_http.py`'s existing `auth_headers_for` pattern where applicable, not a parallel reimplementation.

#### FR-2: At-rest secret encryption via `age`

`steward keys encrypt <file>` / `steward keys decrypt <file>` wrap the `age` CLI (X25519 identities) so secrets live encrypted in Git, never as committed plaintext.

**Consequences (testable):**
- Round-trip encrypt→decrypt of a test fixture reproduces the original bytes exactly.
- Attempting to commit a file matching a configured "looks like a secret" pattern in plaintext is caught by a `steward keys audit` check (not a git hook — v1 is a CLI check, not enforced tooling; see FR-4).

**Out of Scope:** vendoring or reimplementing `age` itself — it is a required external pixi run-dependency, consistent with how `pyforge-warden` treats `deptry`/`osv-scanner` (Decision, technical research OQ2).

#### FR-3: Key rotation

`steward keys rotate --scope <name>` generates a new `age` identity, re-encrypts every secret currently encrypted to the old identity's recipient, and marks the old identity retired in the inventory (FR-5).

**Consequences (testable):**
- After rotation, every previously-encrypted secret decrypts correctly under the new identity and fails to decrypt under the old one.
- Rotation is invocable on-demand (risk/compromise-triggered) — v1 does not ship a calendar-cron scheduler, per the 2026 NIST SP 800-63B Rev 4 shift away from blind time-based rotation (domain research § 4).

#### FR-4: Credential audit / drift detection

`steward keys audit --drift` scans this repo's tracked scripts/config for HTTP-credential-attachment code paths that are not host-scoped (the `JFROG_API_KEY`-class pattern) and reports each as a named finding.

**Consequences (testable):**
- Run against a fixture containing a deliberately unconditional credential-injection pattern (mirroring the historical `_http.py` bug), the audit reports exactly that finding.
- Run against the current, already-fixed `_http.py`, the audit reports clean.

#### FR-5: Credential inventory

`steward keys list` enumerates known credential identities (age recipients, named API-key env vars this repo depends on) with scope and last-rotated metadata, without ever printing a secret value.

**Consequences (testable):**
- Output never contains a raw secret value under any flag combination (enforced by a `meta/` test, mirroring `pyforge-warden`'s `test_socket_deny_alive.py`-style invariant test).

#### FR-6: Revocation record

`steward keys revoke --scope <name>` marks an identity retired in the inventory and prints the manual remediation steps (e.g., "rotate the upstream JFrog token; this tool cannot call JFrog's revocation API").

**Out of Scope:** calling third-party provider revocation APIs (JFrog, GitHub, Anthropic) directly — v1 is a record-and-guide tool, not an API integration; this is a deliberate v1 boundary (§5), not an oversight.

#### FR-7: Remediation regression test

The `JFROG_API_KEY` cross-host leak pattern is closed as a named, automated regression test in Steward's own `tests/conformance/` suite (not just documentation) — this is the PRD's single highest-priority acceptance criterion, per the brief's Success Criteria.

**Consequences (testable):**
- `pixi run -e pyforge-steward pyforge-steward-test` fails if the host-scoping guard (FR-1) is removed or bypassed.

**Feature-specific NFRs:**
- No standing secrets-manager service (no Vault/Infisical-class server) — `keys` operates entirely as a CLI + encrypted files in Git.

---

### 4.2 Deploy (v1 scope: Pages dashboard only)

**Description:** Formalizes the existing hand-run `dashboard-gen` + `git push` loop into a single reconciled command. `presenton-pixi-image` on OpenShift and air-gap bundle installs are explicitly deferred past v1 (Decision D3, §8; §5 non-goals) — the Dream names them as Steward's territory but the "frontier," unbuilt. Realizes UJ-2.

**Functional Requirements:**

#### FR-8: Dashboard build

`steward deploy dashboard --build` runs the existing `dashboard-gen` pixi task (no new build logic — wraps it).

#### FR-9: Reconciled push

`steward deploy dashboard` builds (FR-8), diffs the freshly generated `docs/dashboard/` output against the currently committed tree, and only commits + pushes when a real difference exists.

**Consequences (testable):**
- Running twice in a row with no source changes between runs results in zero commits on the second run.
- A change to `docs/dashboard/generate.py`'s output is reflected in exactly one new commit.

#### FR-10: Dry-run

`steward deploy dashboard --dry-run` performs the build and diff (FR-8, FR-9) and prints the diff without committing or pushing.

#### FR-11: Deploy status

`steward deploy status` reports the last successful dashboard deploy (commit SHA, timestamp), read from Git history — no separate state store.

**Feature-specific NFRs:**
- No standing GitOps control plane (no ArgoCD/Flux) — deploy is a CLI-invoked reconciliation step, run manually or from an existing workflow, not a continuously-running controller (Decision D6, §8).
- Uses the repo's existing GitHub Pages branch-based publishing (native, zero new GitHub Actions workflow in v1) — Decision D6.

---

### 4.3 Provision

**Description:** A thin CLI face over the pixi environment estate and `scripts/bmad-loop-worktree`, not a new environment-management system. Steward does not take ownership of Marshal's multi-project/worktree machinery (Decision D4, §8) — it invokes it. Realizes UJ-3.

**Functional Requirements:**

#### FR-12: Environment materialization

`steward provision --env <name>` resolves `<name>` against pixi.toml's `[environments]` table and runs `pixi install -e <name>`, or reports a clear error listing valid environment names if `<name>` doesn't exist.

#### FR-13: Runner provisioning

`steward provision --runner bmad-loop --env <name>` wraps `scripts/bmad-loop-worktree` to materialize a loop worktree and its named pixi environment together, in one call.

**Out of Scope:** reimplementing `bmad-loop-worktree`'s internals — Steward calls it, does not fork or own its logic.

#### FR-14: Environment inventory

`steward provision --list` enumerates every environment in pixi.toml's `[environments]` table with the features composing it (read-only introspection, no pixi TOML parsing reimplementation beyond what's needed to list names/features).

#### FR-15: Sync-gate check

`steward provision --verify` wraps the existing `environment.yaml` ↔ `pixi.toml` sync-gate check (`pixi project export conda-environment -e build` comparison) and reports drift, rather than reimplementing the check logic that already backs the repo's CI gate (CLAUDE.md § "PR CI gates").

**Feature-specific NFRs:**
- Steward never invokes pixi at build/import time for its own packaging (matches `pyforge-warden`'s "pixi is a build/dev-env floor, never a runtime dependency" NFR) — `provision`'s pixi invocations are explicit, user-triggered CLI actions, not import-time side effects.

---

### 4.4 Budget

**Description:** Makes the "$1500/month locked" doctrine machine-readable. v1 is deliberately conservative — a declared ceiling plus a minimal, honest check — because there is no live cloud spend in this repo today to meter against (Decision D1, §8; domain research § 5's grounding gap). Realizes UJ-4.

**Functional Requirements:**

#### FR-16: Ceiling declaration

`steward budget set --cap <amount><currency>/<period>` (e.g. `1500usd/month`) records a machine-readable ceiling to a tracked config file under Steward's own config surface.

#### FR-17: Ceiling display

`steward budget show` prints the currently declared ceiling(s) in both human-readable and `--json` form.

#### FR-18: Manual check (honest stub)

`steward budget check` is an extension point that, in v1, has no live metered-spend source to check against, and explicitly reports "no metered spend source configured" rather than fabricating a number or silently passing.

**Consequences (testable):**
- `steward budget check` exits non-zero-but-distinct (a dedicated "not configured" exit code, not the same as a breach) when no spend source is wired up, so scripts calling it can distinguish "no data" from "under budget" from "over budget."

**Out of Scope:** any Kubecost/OpenCost/Infracost-class integration, any cloud-provider budget-API polling — deferred until real cloud spend exists to meter (§5).

## 5. Non-Goals (Explicit)

- **No standing secrets-manager service** (Vault-, Infisical-, or OpenBao-class server) — `keys` is a CLI + encrypted files only.
- **No Backstage-class software catalog or scaffolder platform** — `provision` is a CLI face over pixi, not a new IDP.
- **No ArgoCD/Flux-class GitOps control plane** — `deploy`'s reconciliation is CLI-invoked, not a standing controller.
- **No Kubecost/OpenCost/Infracost-class cost-allocation integration** in v1 — no live cloud spend exists to allocate against yet.
- **No third-party credential-revocation API integration** (JFrog, GitHub, Anthropic, etc.) — `keys revoke` records intent and guides manual remediation, it does not call out to provider APIs.
- **No `presenton-pixi-image` on OpenShift or air-gap bundle install support in v1** — named in the Dream as Steward's eventual territory, explicitly deferred; `deploy`'s v1 scope is the Pages dashboard only.
- **No multi-operator / team features** — Steward is single-operator dogfooded tooling, not a product for external users.
- **No calendar-based automatic key rotation scheduler** — rotation in v1 is on-demand/risk-triggered, per current (2026) credential-lifecycle best practice.

## 6. MVP Scope

### 6.1 In Scope

- `steward keys`: host-scoped credential resolution, `age`-based at-rest encryption, on-demand rotation, drift audit, inventory, revocation records, and the `JFROG_API_KEY` regression test (FR-1–FR-7).
- `steward deploy dashboard`: build, reconciled push, dry-run, status (FR-8–FR-11).
- `steward provision`: environment materialization, runner provisioning wrapper, inventory, sync-gate check (FR-12–FR-15).
- `steward budget`: ceiling declaration, display, honest manual-check stub (FR-16–FR-18).
- Packaging as a `pyforge-warden`-pattern pixi workspace member: `src/shared/packages/pyforge-steward/`, `hatchling` build backend, `argparse` CLI (Decision D5, §8), lean dependency posture, `unit`/`conformance`/`meta` test-tier split, dogfooding test (Steward provisioning its own dev environment / auditing this repo's own credential surface).

### 6.2 Out of Scope for MVP

- Everything in §5 Non-Goals.
- `presenton-pixi-image` OpenShift deploy and air-gap bundle installs — deferred to a future epic once `deploy`'s v1 (Pages) ships and proves the reconciliation pattern. `[NOTE FOR PM]`: this is the Dream's most emotionally load-bearing deferred item — revisit once the enterprise-airgap Dream's other frontier item (`deckcraft`) also progresses, since both share the OpenShift/air-gap substrate.
- Automated budget enforcement/alerting — deferred until real cloud spend exists.
- A formal GitHub Actions deploy workflow for the dashboard (v1 uses direct push to the existing Pages-serving branch) — deferred to v2 if push-button/scheduled automation becomes wanted.

## 7. Success Metrics

**Primary**
- **SM-1**: The `JFROG_API_KEY` cross-host leak pattern has a passing, named regression test in Steward's `conformance/` suite. Validates FR-7.
- **SM-2**: `steward deploy dashboard` replaces 100% of manual `dashboard-gen` + push invocations going forward (measured by: no more hand-run occurrences in the operator's own workflow after Steward ships). Validates FR-8–FR-11.
- **SM-3**: `steward provision --env <name>` succeeds for every entry in pixi.toml's `[environments]` table without the operator needing to consult raw pixi syntax. Validates FR-12, FR-14.

**Secondary**
- **SM-4**: `steward budget show` is queried at least once after any Dream/spec update that touches the ceiling doctrine, replacing a Dream-file grep. Validates FR-16, FR-17.

**Counter-metrics (do not optimize)**
- **SM-C1**: Number of duties/features shipped is *not* optimized — a `budget` duty that grows Kubecost-scale integration before any live spend exists would be over-building against this PRD's own non-goals (§5). Counterbalances any pressure to "complete" all four duties symmetrically.
- **SM-C2**: `keys` rotation frequency is *not* optimized as a vanity metric (more rotations ≠ better) — 2026 best practice is risk-triggered, not frequency-maximizing (§4.1 FR-3). Counterbalances a naive "rotate more often" instinct.

## 8. Decisions on Open Questions (from research + brief)

Every open question the brief carried forward now has an explicit PRD decision. Confidence is noted; low-confidence decisions should be re-confirmed at the architecture step, not silently trusted.

- **D1 (was OQ1, budget scope) — DECIDED, high confidence.** v1 ships a declared ceiling + an honest "not configured" manual check (FR-16–FR-18), no automated enforcement. Rationale: no live spend exists to enforce against (domain research § 5); shipping a doctrine + honest stub is more useful than either silence or a fake enforcement mechanism.
- **D2 (was OQ2, keys implementation) — DECIDED, medium confidence.** `age` for at-rest encryption (FR-2), not an Infisical-class server. Rationale: matches this repo's existing "nothing committed, env-vars only" doctrine and requires no standing service. **Flag for architecture confirmation** — this is the lower-confidence decision in this PRD; if Steward's actual secret inventory grows past a handful of API keys, this decision should be revisited.
- **D3 (was OQ3, deploy v1 boundary) — DECIDED, high confidence.** v1's `deploy` scope is the Pages dashboard only; `presenton-pixi-image`/air-gap bundle deploy is explicitly deferred (§6.2).
- **D4 (was OQ4, Steward/Marshal provisioning boundary) — DECIDED, high confidence.** Steward's `provision` duty invokes existing Marshal-owned machinery (`scripts/bmad-loop-worktree`, the pixi `[environments]` table) via CLI wrapper (FR-12–FR-15); it does not take ownership of or modify that machinery's implementation. Marshal retains ownership of multi-project/worktree machinery per the Ecosystem Crew Dream's 2026-07-23 assignment.
- **D5 (was OQ5, CLI framework) — RESOLVED as fact, not a product decision.** `argparse`, confirmed by directly reading `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` (uses plain `argparse`, not Click/Typer). Steward matches its packaging sibling for consistency.
- **D6 (was OQ6, deploy mechanism) — DECIDED, medium confidence.** v1 uses direct push to the existing Pages-serving branch (native GitHub behavior, zero new Actions workflow), invoked via `steward deploy dashboard` run by the operator or an existing workflow — not a new `upload-pages-artifact`/`deploy-pages` or `peaceiris/actions-gh-pages` Actions workflow. Rationale: matches today's actual manual process shape and keeps v1 minimal; **flag for revisit** if scheduled/push-button automation becomes a real want (§6.2).

## 9. Open Questions

1. Should `steward keys`' credential inventory (FR-5) include non-Steward-issued credentials this repo already depends on (e.g. `GITHUB_USERNAME`/token, `sk-ant` key) for audit visibility, or only credentials Steward itself issues going forward? Leans toward "include for audit visibility" but not decided here — architecture should confirm scope against FR-4's drift-audit needs.
2. What does "host allowlist" configuration look like concretely for FR-1 — a config file Steward owns, or does it read `_http.py`'s existing `*_BASE_URL` env-var table directly? Architecture-level design question, not resolved in this PRD.
3. Does `steward budget`'s config file (FR-16) live under `_bmad-output/projects/pyforge-steward/` or under a repo-root Steward config location usable independent of any active BMAD project? Affects whether the ceiling doctrine survives a `bmad-switch` to a different active project.

## 10. Assumptions Index

- From §2.2 — Steward has exactly one user (this repo's maintainer) and no team/multi-tenant surface; not independently re-validated with the user this session, carried from the product brief's own assumption A3.
- From §4.1 FR-6 — third-party revocation-API integration is out of scope for v1 because Steward has no existing credential to call such APIs with today; this is inferred from the repo's current tooling, not confirmed by the user.
- From §4.4 — the "$1500/month" figure in FR-16's example is illustrative, carried verbatim from the Dream's own CLI cadence example (`docs/dreams/ecosystem-crew.md` § 8); the actual ceiling value is a config input, not a PRD claim about real spend.

## 11. Epic-Level Groupings (handoff to architecture / epics-stories)

Sequenced per the domain-research report's recommendation (proven urgency first, most-speculative last):

- **Epic A — Keys** (FR-1–FR-7): highest priority, closes two already-dated real incidents.
- **Epic B — Deploy** (FR-8–FR-11): formalizes an existing working manual process.
- **Epic C — Provision** (FR-12–FR-15): thin wrapper over an already-good substrate.
- **Epic D — Budget** (FR-16–FR-18): most conservative scope, least locally-grounded duty.
- **Epic E — Packaging & Test Scaffold** (cross-cutting, likely Epic 0 in practice): the `pyforge-warden`-pattern pixi workspace member setup (§6.1 packaging bullet) that Epics A-D all depend on — architecture should confirm whether this is its own epic or folded into Epic A's first story.

---

**Research grounding:** `_bmad-output/projects/pyforge-steward/planning-artifacts/research/domain-steward-platform-ops-tooling-research-2026-07-25.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-steward-pixi-workspace-member-research-2026-07-25.md`.
**Brief:** `_bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md`.
