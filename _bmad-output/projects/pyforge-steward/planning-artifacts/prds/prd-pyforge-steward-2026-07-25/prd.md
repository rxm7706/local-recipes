---
fr-derivation-from: "2026-09-17"
title: Steward (pyforge-steward)
created: 2026-07-25
updated: "2026-09-24"   # RE-STAMPED 2026-09-24: chain-currency (spec→prd) — Story 63.4 (steward session check) landing entries on spec-pyforge-steward's and spec-pyforge-core's .memlog.md; § Currency reconciliation — 2026-09-24 appended. Prior 2026-09-20
status: final
currency_review: "Reviewed 2026-09-24 — chain-currency (spec→prd) — spec-pyforge-steward's .memlog.md moved to 2026-09-24T20:08 (Story 63.4, `steward session check`, plus a merge reconcile of a co-governor spec-pyforge-core memlog entry from concurrent marshal Story 46.2 landing) while this PRD sat at 2026-09-20 — four days, past the runbook's 2-day grace. Story 63.4 decomposes Epic 63 (`environment pyforge-guild`, spec-pyforge-steward CAP-5), consolidating seven pre-existing session-precondition findings into one `pyforge steward session check` duty wired into four entry points; CAP-5 already covers the pyforge-guild environment-default capability this duty verifies. No FR added or changed. Reconciled in § Currency reconciliation — 2026-09-24. FR delta: none. Prior — Reviewed 2026-09-20 — chain-currency (spec→prd) — spec-pyforge-steward's .memlog.md moved to 2026-09-20T02:28 with the landing entries for Stories 61.1–61.3 (corridor transports, work passport + core schema, as-of glass and mailed query — CAP-141..143 realized, Epic 61 in progress) plus the DW-FU-61-2 closure and two co-governor reconciles, while this PRD sat at 2026-09-17. All three stories decompose Spec capabilities already folded 2026-09-17; no FR added or changed. Reconciled in § Currency reconciliation — 2026-09-20. FR delta: none. Prior — Reviewed 2026-09-17 — chain-currency (spec→prd) — one-chain steward fold reminted spec-pyforge-steward CAP-1..145 (31 absorbed Specs, 35 covers-dreams) while this PRD sat at 2026-09-14 with fr-derivation-from already 2026-09-17. Kernel FR-1..18 unchanged; absorbed CAPs were already decomposed as Epics 9–64 on their own Specs — remint is provenance, not a new FR set. Reconciled in § Currency reconciliation — 2026-09-17. FR delta: none. Prior — Reviewed 2026-09-14 — chain-currency (spec→prd) — spec-pyforge-steward's own SPEC.md moved to 2026-09-12 (a 4-path surface-drift-exclude block; dated verified: lines on CAP-1..CAP-4 from the 2026-09-11 sweep, all holding, one scoped honestly as not-re-exercised-live) and its memlog to 2026-09-13T23:59 (a bulk post-outage surface reconcile of five already-landed stories, plus Story 53.6's frames.py re-key from `name` onto `identifier` per Frame Spec v0.3 §4.2.1) while this PRD sat at 2026-09-08. Reconciled in § Currency reconciliation — 2026-09-14. FR delta: none. Prior — Reviewed 2026-09-09 — chain-currency (spec→prd) — spec-pyforge-unifying-strategy's `SPEC.md` re-stamped 2026-09-09 by `bmad-correct-course` (operator-approved `sprint-change-proposal-2026-09-09-currency-review.md`): `:488` line-count constraint retired by operator ruling, `:73`/`:315` Python floor corrected to `3.14.*`, a dated Constraints block, § Residual (2026-09-09) replacing \"none\", two `open_questions`. Checked against FR-1..31 — no FR added or changed; the realization gate is a definition-of-done discipline over existing requirements, and Epics 48–49 decompose the Spec's Residual and Constraints, not a requirement here. § 14 gained a dated paragraph; deltas in § Currency reconciliation — 2026-09-09. Reviewed 2026-09-08 — chain-currency (spec→prd) — spec-pyforge-steward's `.memlog.md` moved 2026-09-08 for the deferred-work sweep follow-ups; the one substantive motion is `_persona_mentions` in tests/meta/test_adoption_register.py gaining word-boundary matching and a widened scan (README.md + reference/*.md). Checked against FR-1..31 — this PRD states no requirement about the adoption register or persona-routing text (searched for `adoption register` and `persona mention`, zero hits), so this is a test-helper precision fix inside an already-decomposed story surface and adds no FR; one new story was authored on the epics side (43.7, re-homing mason DW-13-2-2's sidecar 3.14 runtime validation), which decomposes existing pap:CAP-5/CAP-6 rather than minting a requirement here. Deltas in § Currency reconciliation — 2026-09-08. Reviewed 2026-09-05 — chain-currency (spec→prd) — spec-pyforge-steward's .memlog.md moved twice on 2026-09-05 (the post-merge follow-up-review landing, PR #1056, and the bmad-suite 2026.9.5 roster change) and spec-bmad-eval-quality was created the same day (CAP-1 suite membership, CAP-2 pilot contract → Epic 45); neither adds an FR here — suite membership is governed by spec-bmad-suite-channel-product / -metapackage and eval-quality decomposes from its own owned Spec; deltas in § Currency reconciliation — 2026-09-05. Reviewed 2026-09-02 — chain-currency: spec-pyforge-steward's 2026-09-01 git touch (de24e396, the 23-1 merge) is the Spec landing at its sharded path `specs/spec-pyforge-steward/SPEC.md`; CAP-1..4, AD-1..9, non-goals and success signal are unchanged against this PRD, so no FR changes. Same day the red-team correct-courses minted Epics 40–43 on the unifying chain; those bind spec-pyforge-unifying-strategy, not this PRD. Reviewed 2026-08-29 — reconciled against spec-pyforge-steward's spec-surface drift catch-up and the retroactive Epic 38 decomposition; FR-1..31 unchanged, zero new capability; deltas recorded in § Currency reconciliation — 2026-08-29 (previously 2026-08-26)."
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
- **UJ-2.** The operator, having edited `pyforge.doctor.sources.fleet_scan`, runs `steward deploy dashboard` once and trusts that nothing happens if there's no real diff, and a clean reconciled commit+push happens if there is. Realizes FR-8–FR-11.
- **UJ-3.** A bmad-loop session, needing the `pyforge-atlas` environment for a new worktree, runs `steward provision --env pyforge-atlas` instead of recalling the raw `pixi install -e` invocation. Realizes FR-12, FR-13.
- **UJ-4.** The operator, six months from now, runs `steward budget show` to remember what ceiling was declared and when, instead of grepping Dream files. Realizes FR-16, FR-17.

## 3. Glossary

- **Duty** — one of Steward's four independently-shippable responsibility areas: keys, deploy, provision, budget. Each duty is an engine module behind a shared interface (mirrors `pyforge-warden`'s `interfaces.py` pattern).
- **Host-scoped credential** — a credential whose attachment to an outbound HTTP request is gated by the request's destination host, not attached unconditionally (the fix-shape for the `JFROG_API_KEY` leak pattern).
- **Reconciliation** — a deploy step that diffs current-vs-desired state and only acts (commits/pushes) when a real difference exists, rather than blindly re-applying every run.
- **Ceiling** — a machine-readable declared resource-spend limit (e.g. `1500usd/month`), distinct from *enforcement* (checking live spend against the ceiling), which v1 does not implement.
- **pixi environment estate** — the named entries in this repo's root `pixi.toml` `[environments]` table (~14 at authoring time: `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`, `pyforge-warden`, `pyforge-atlas`, `bmad-ui`, and combinations; **27 as of 2026-08-26** — the count is derived from the table at run time, never hardcoded in Steward).
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
- A change to `pyforge.doctor.sources.fleet_scan`'s output is reflected in exactly one new commit.

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

---

## The station's own backlog — three Specs decomposed 2026-08-08

Until today this PRD decomposed Steward's **shipped** surface (`FR-1..FR-18`: keys,
deploy, provision, budget) and nothing else, while three `status: draft` Specs sat in
`planning-artifacts/specs/` with no FR, no epic and no story. Steward therefore rendered
**18/18 · 100%** while owning three undecomposed Dreams.

This is the same rule Marshal's PRD adopted the same day, applied here: **a capability
decomposes into this PRD iff its Dream is `owner: steward`** — not iff it touches a
particular directory. Two of the three arrived at Steward today (`jira-github-projects-sync`
re-owned under the build-line/estate seam), which is precisely why the gap was invisible.

### Module provisioning — `spec-bmad-module-provisioning` (FR-19..FR-21)

*Sequencing: land before the container work — `provision --module` inside an image build
only exists if the backend exists first.*

#### FR-19: One-command module provisioning
An operator materializes a named BMAD module without recalling its installer's syntax.
**Consequences:** `provision --module <name>` succeeds for each supported module; an
unknown name lists valid ones rather than surfacing the underlying tool's raw error;
the implementation is a **subprocess wrap of the module's own installer** (AD-1), never
a reimplementation.

#### FR-20: Module discovery
An operator can ask what modules exist and which are installed before choosing.
**Consequences:** `provision --list-modules` enumerates supported modules with installed
state; state is **derived from the filesystem**, not from a hand-maintained declaration.

#### FR-21: Partial state is named, never silent
**Consequences:** an installer that exits non-zero, or succeeds while leaving the module
unimportable, is reported as a named failure — never counted as provisioned.

### The one-container Guild — `spec-unified-container` (FR-22..FR-26)

#### FR-22: One build, whole Guild
**Consequences:** a single `Containerfile` produces an image carrying all eight station
CLIs; each answers `--version` inside the container.

#### FR-23: The image ships the repo at a fixed short path
**Consequences:** the checkout lives at a path short enough to avoid the documented
`pixi-build-python` path-length panic; the path is fixed and documented, not derived
from the build host.

#### FR-24: Credentials never enter image layers
**Consequences:** no secret is present in any layer — asserted by a build-time scan;
credentials arrive at run time only, through Steward's existing `keys` surface.

#### FR-25: State outlives the container
**Consequences:** loop homes, the Tier-3 store and mutable runtime caches resolve to
mounted volumes; a container restart loses no durable state, proven by a round-trip test.

#### FR-26: The image proves itself at build time
**Consequences:** the build runs a smoke gate that fails the build — not a later run —
when any station CLI is missing, unimportable, or over its documented start-up budget.

### Two boards, one truth — `spec-jira-github-projects-sync` (FR-27..FR-31)

*Greenfield at authoring time (2026-08-08): nothing existed. Three open questions remained
in the Spec (authoritative side, Mode A vs B, Mode B's schema); **Q1/Q5 were resolved
2026-08-08** — an external board pair, hence Steward's, hence these FRs. **Since shipped:**
Epic 8 landed 2026-08-09..13 as Stories 8.1–8.7, extending FR-27..31 with the schedule
trigger (8.4) and assignee/identity-link propagation (8.7).*

#### FR-27: Bidirectional propagation
**Consequences:** a status/assignee/link change on either board reaches the other with no
human action on the receiving side, demonstrated against a live pair.

#### FR-28: Zero-loop guarantee
**Consequences:** N round-trips of one human change produce **exactly one** propagation,
not N — demonstrated by test, never asserted.

#### FR-29: Idempotent update processing
**Consequences:** delivering an identical payload twice leaves both systems byte-identical
to delivering it once.

#### FR-30: Fail loud, fail alone
**Consequences:** an item missing its cross-system link emits a named, greppable error and
does not stop the batch for every other item.

#### FR-31: Explicit status-vocabulary translation
**Consequences:** every status crossing the boundary passes through a reviewable mapping;
an unmapped value is a hard logged failure, never a pass-through that invents a state.


## Satellite: Canopy — the Canopy mounts the eight stations

> **Folded into this PRD 2026-09-08.** Was `prd-pyforge-unifying-strategy-2026-08-24`, a run-folder named for a CHAIN
> rather than this project — upstream's pattern is `prd-{project_name}-{date}`.
> Its requirements keep their own numbering, qualified `canopy:FR-n`, which is how every
> citation now spells them after the 2026-09-08 attribution pass (807 bare FR citations
> read down; 277 resolved by chain-owning path, 352 by epic section and id range).
> **No citation changes meaning.** Renumbering was rejected for the same measured reason
> as the spines: the mechanical attributors top out at 47-80% accuracy.
>
> Original frontmatter — status: in-progress, updated: 2026-08-31.




### 0. Document Purpose

This PRD decomposes `spec-pyforge-unifying-strategy` into functional requirements an epic pass can
group and a dev session can implement. **The SPEC is the contract; this document is its
decomposition.** Where they disagree, the SPEC wins and this document is wrong.

Every FR carries the capability ID it realizes. Nothing here floats: an FR with no CAP is scope
creep, and a CAP with no FR is an unmet contract. The traceability check at §12 is mechanical for
exactly that reason.

Two things this PRD deliberately does not do. It does not restate what `spec-python-agent-platform`
already shipped — `convergence.md` is the authority on that boundary, and re-specifying a `done`
surface is how an extension quietly becomes a rewrite. And it does not choose mechanisms; those
live in `addendum.md` and the architecture pass, except where a mechanism was already decided and
recorded, in which case the FR names it as a constraint rather than pretending it is open.

### 1. Vision

An operator signs in once and the whole estate is in front of them: a published front page, eight
station portals, an analytical board that shows them only their own rows. An agent addresses the
same eight stations through one grammar and one service shape, and survives the connection dropping
mid-build. A station's action becomes an event another station acts on. All of it inside an
egress-blocked namespace where the application cannot alter its own schema.

The Canopy already proved this is reachable. **The 2026-08-25 drain landed the eight portals,
chrome, host MCP faces, dispatch, events, and the governed-DDL path in code.** Closeout
**2026-08-26:** Lane 1 `/` **200**, CAP-9 `platform_app` DML-only proven, Liquibase
`:17`–`:19` executed. Isolated `mfa` sqlmigrate stays fake. Not a `services/` rewrite.
**2026-08-26 evergreen:** CAP-19 (query plane) reopens this PRD. CAP-1..18 stay shipped
slices. Rebuild of private analytical stores is in scope.
**Same-day first slice:** Epic 34.1–34.5 + Lane 3 36.1–36.2 (`estate-cache`)
shipped. Five-tier SM-5 holds (37.1, 40/40; mason skill = `conda-forge-expert`).
Residual: SPEC OQs `query-plane-face` / `query-plane-catalog` /
`query-plane-scribe-cutover`. Mosaic optional. Do not re-dispatch 18–37.

### 2. Target User

Four users, and the fourth is not a person. That is load-bearing rather than cute: several of the
nineteen capabilities exist mainly to make the estate legible to something that is not a human, and
a requirement written only for the human reader will under-specify them. CAP-19 adds the
**query** as a shared job — dashboards and agents must share one plane.

#### 2.1 Jobs To Be Done

| User | Job | Blocked today by |
|---|---|---|
| **Platform operator** (steward's own audience) | Deploy, upgrade and audit the estate in a regulated namespace | Schema change is whatever the migration graph did; the app's role can alter its own schema |
| **Compliance auditor** | Move from a finding to the package, build and fleet context around it | Warden's portal exists and shows compliance; nothing else has a portal |
| **Packaging / platform engineer** | Drive any station without learning eight tools | Eight CLIs, eight verb vocabularies, eight output shapes |
| **Autonomous agent** | Perform a station's work programmatically and reliably | One station of eight has a service face; long operations die with the connection |
| **Dashboard / agent query** | Ask the estate a question (metric, SQL, neighbor) | First plane slice shipped; residual is face / catalog / Scribe-pgvector OQs — not a second engine |

#### 2.2 Non-Users

- **The public.** Lane 1 is a front door for the estate's own operators, reachable only behind the
  identity provider. "Public" in CAP-2 means "not gated per-page", not "unauthenticated".
- **External API consumers.** CAP-4's service face is for estate callers and estate agents. No
  external contract, no versioning promise to third parties.
- **Multi-tenant customers.** CAP-7's row isolation is per-user row filtering on analytical boards,
  not a tenancy layer, and nothing here makes the estate multi-tenant.

#### 2.3 Key User Journeys

**UJ-1 — One session, four surfaces.** An operator opens the estate root, reads a runbook page an
editor published this morning without a deploy, uses the app switcher to jump to the packaging
station's portal, follows a link into an analytical board, and sees only rows their role permits.
They authenticate once, at the start, and never change origin.

**UJ-2 — The agent that survives the proxy.** An agent connects to a station's service face,
starts an operation that takes several minutes, and loses its connection to a router that closes
idle streams at thirty seconds. It reconnects, re-attaches to the same operation, and collects the
result. Nothing is recomputed and nothing is lost.

**UJ-3 — The event that crosses stations.** A build completes. The event is published once and a
different station consumes it and acts. A malformed event published by a buggy producer lands in a
dead-letter queue after its retry budget rather than blocking the group forever, and an operator
can see it there.

**UJ-4 — The audited upgrade.** An operator runs a chart upgrade. A governed changeset applies the
schema change under a role that holds DDL rights; the application's own role does not and provably
cannot. The application then starts and its framework bookkeeping still runs. The change is
attributable to a reviewed changeset, not to whatever an ORM decided to emit.

**UJ-5 — The flag flip.** An operator changes one flag value. Web, service and CLI surfaces all
observe the new behaviour, with no redeploy and no outbound network call.

**UJ-6 — The query that misses OLTP.** A Vizro board and a DB-GPT Text-to-SQL ask the same
estate question. Both read the query plane (live attach for a declared view, Parquet for a
scan, `vss` for a neighbor). Neither opens a private DuckDB or Chroma, and neither is
given the OLTP DSN. A guessed `SELECT` against the system of record is a refused
configuration, not a hot table.

### 3. Glossary

Defined once. The rest of the document uses these exactly, and no synonyms.

- **Canopy** — the Django host at `src/platform/`. Live today. Not renamed by this chain.
- **Station** — one of the eight PyForge capability domains: warden, atlas, mason, marshal, doctor,
  herald, scribe, steward. The roster is fixed at eight.
- **Lane 1** — the CMS-managed front door mounted at `/`.
- **Lane 2** — a station's server-rendered portal, mounted under the Canopy as a Django app.
- **Lane 3** — an analytical board surface, reached through the Canopy, isolated per user.
- **Service face** — a station's programmatic endpoint, spoken over the current MCP specification.
- **Five-tier symmetry** — an **03** station capability is complete when it has all five of: CLI,
  portal, service face, domain skill, persona. The eight stations are 03. 01/02 work is complete
  at spec + script/analysis or spec + skill and is not measured on this matrix.
- **work_class** — 01 one-off, 02 short-term (spec + skill), 03 long-term (capability + owner +
  SLA). Estate operating model (Dream Grounding Q1–Q2).
- **Path A / Path B** — 03 is deterministic code (Path A) or agentic work through the Agent
  Canopy and a station persona (Path B). **Tachyon** is a production LLM provider adapter, not
  Path B and not a product.
- **Domain skill** — an agent-loadable document encoding how a station's work is actually done.
- **Persona** — an autonomous agent bound to one station, acting only through that station's
  command grammar and service face.
- **Chrome** — the app switcher, base layout and theme assets shared by every portal. Owned by one
  package; never by a portal.
- **Governed changeset** — a reviewed, versioned schema-change unit applied by an authority holding
  DDL privilege, distinct from the application's own migration bookkeeping.
- **Feedstock** — a conda-forge recipe. Six are new work in this chain.
- **Hooks and plugins** — architecture principle (canopy:AD-21): a process owns
  hook specifications; a plugin replaces or extends a layer without a fork.
  Kedro names the split; it does not require a Kedro project. **CAP-18** is the
  shared contract (not a scorecard). Q8 is the PR-gate instance (Warden owns
  those specs; scanners are plugins).
- **Query plane** — the one DuckDB analytical engine (live read-only Postgres
  attach, Kedro Parquet cache, `vss` vectors). Stations and agents are clients.
  Platform Postgres stays OLTP / app state. **CAP-19**, canopy:AD-22.

### 4. Features

Sixteen features over nineteen capabilities (CAP-1..19). Grouped by delivery seam, which is also
how the epic pass groups them. Canopy Epics 18–30 do **not** implement CAP-18; that is Epic 32
plus Warden Epic 9 plus per-station process-hook stories. **CAP-19 is Epic 34.**

---

#### 4.1 Shared chrome

**Description.** One installable Django app supplies everything a portal needs to look and behave
like part of the estate: the app switcher, an OIDC-aware base layout, the Modernist theme assets,
and the seam by which a portal registers itself with the host. It is built first because
everything visual depends on it, and a portal built before it exists will grow its own chrome that
nobody removes later. Realizes UJ-1.

Nothing off-the-shelf supplies this. `django-lasuite` — which the Dream named — is OIDC, DRF and
malware-scanning plumbing with no switcher and no theme, and La Suite's own switcher ships as
npm/React against a service-list endpoint unreachable in an air gap. This package is ours.

**Functional Requirements:**

##### canopy:FR-1: Chrome is installable, and singular

A portal author installs one package and receives the estate's chrome. Realizes UJ-1. **CAP-1.**

**Consequences (testable):**
- Two portals render byte-identical chrome markup sourced from the package.
- A test enumerates portal template and static directories and **fails** if any portal ships its
  own copy of a base layout, app-switcher template, or theme asset.
- Removing the package from `INSTALLED_APPS` breaks both portals identically.
- Registration carries owner station slug, backup, `work_class`, and promotion date. The SLA
  body is not a chrome / AppConfig field (it stays in the 03 BMAD spec).

##### canopy:FR-2: A portal registers itself without host edits

Adding or removing a station portal changes no host code outside that portal's own registration.
**CAP-1, CAP-3.**

**Consequences (testable):**
- Adding a portal requires no edit to the host's root URLconf or settings beyond an entry the
  portal itself supplies.
- Removing a portal leaves the host booting and the remaining portals rendering.
- The app switcher's entries derive from what is registered, not from a hand-maintained list.
- A portal registering outside the `/stations/<name>/` prefix fails a check.
- The switcher and Guildhall do **not** tile a registration with `work_class` 01 or 02 as a
  first-class station surface.

##### canopy:FR-3: The switcher shows only what the user may reach

The app switcher renders the stations the signed-in user is authorized for. **CAP-1, CAP-12.**

**Consequences (testable):**
- A user lacking a station's role does not see it in the switcher.
- The switcher is not the enforcement point — requesting a hidden station's URL directly is still
  refused by that station's own authorization.

**Notes:** The estate's existing portal (`compliance_face`) mounts at `/compliance/`, not under a
`/stations/` prefix. **Decided 2026-08-24: uniform prefix, and `compliance_face` moves** — see
canopy:FR-9a. The pre-audit draft asserted `/stations/{station}/` as an inherited convention; it was not,
and choosing it now is a decision with a migration attached rather than a free default.

---

#### 4.2 Lane 1, the front door that replaces a console

**Description.** A CMS-managed front door at `/` whose pages are edited and published without a
code deploy, with its admin reachable only through the identity provider. It **supersedes** the
estate's existing statically-built console rather than sitting beside it — so this feature carries
a migration obligation, and the ordering inside it is the whole point: parity is proven before the
old build path is removed. Realizes UJ-1.

Wagtail carries it alone. CodeRed CMS was ruled out on maintenance evidence.

**Functional Requirements:**

##### canopy:FR-4: Content publishes without a deploy

An editor changes a page and the change is live with no code deploy and no pod restart.
Realizes UJ-1. **CAP-2.**

**Consequences (testable):**
- A page edit is visible to an anonymous-within-estate request without a new image or a rollout.
- Content survives a pod restart and is visible identically from every replica.

##### canopy:FR-5: The CMS admin is behind the estate identity provider

An unauthenticated request to the CMS admin is redirected to the identity provider, not to a local
login form. **CAP-2, CAP-12.**

**Consequences (testable):**
- The admin login URL resolves to the IdP; no local password form is reachable.
- Local password management and email-management surfaces are disabled.
- A user who authenticates but holds no group granting CMS admin access is refused **with a
  comprehensible error**, not an unexplained bounce.

**Notes:** The last consequence is the one that bites. CMS admin access gates on a specific
permission rather than a generic staff flag, and OIDC users arrive with no groups — so a correctly
authenticated user is refused by default until claim-to-group mapping exists. There is no
first-party guidance for this; treat it as real work, not configuration.

##### canopy:FR-6: Console parity is inventoried before anything is removed

Every view the retired console offers is enumerated and classified as runtime-reproducible or
build-time-only **before** the cutover. **CAP-2. Satisfied 2026-08-24** by
`specs/spec-pyforge-unifying-strategy/console-parity-inventory.md`.

**Consequences (testable):**
- An inventory artifact exists listing every console view with its data source and classification.
  **Done:** 23 surfaces — 14 runtime-reproducible, 7 build-time-only, 3 mixed.
- Any view classified build-time-only is escalated as a scope decision rather than silently
  dropped. **Done:** the seven reduce to four decisions, recorded in the inventory.
- The inventory is the cutover's precondition: canopy:FR-7 cannot start until it is complete.

**Notes:** The four decisions are live run state (three surfaces, one decision), detector verdicts,
curated editorial content, and journal-derived timing. The fifth build-time-only item — the
committed-snapshot delivery model — is not a loss to mitigate; removing it is the point of CAP-2.

##### canopy:FR-7: The old build path is removed, not unlinked

After parity, the console's generation pipeline is deleted — not merely delisted from navigation.
**CAP-2.**

**Consequences (testable):**
- The generator, its four pixi tasks, its scheduled workflow trigger, and the committed data blob
  are gone.
- No inbound reference to the retired path remains in docs, workflows, specs, presentations,
  scripts or tests.
- The co-published Kedro-Viz tree **survives** — it has its own workflow and no inbound link from
  the console, so it is not part of this obligation and must not be deleted with it.
- Downstream parsers of the committed data blob are identified and migrated first.
- `spec-factory-console` is marked superseded in the same chain — a superseded spec still claiming
  ownership is a worse outcome than two consoles.

**Notes:** `[NOTE FOR PM]` the inventory found **over 100 inbound references** to the console path
across dreams, specs, presentations, pixi tasks, workflows, tests and scripts — including the
Charter's own accountability gate. The reference sweep is its own story, not cleanup at the end of
another one. The inventory recommends splitting this feature's retirement into three stories:
inventory (done), parity build, removal.

##### canopy:FR-8: Media and cache survive multiple replicas

Lane 1 operates correctly with more than one replica. **CAP-2.**

**Consequences (testable):**
- Uploaded media is retrievable from a replica that did not receive the upload.
- An image rendition generated by one replica is served by another without regeneration.
- No Lane 1 state depends on pod-local disk.

**Feature-specific NFRs:**
- Search uses the database backend (PostgreSQL full-text). No fourth backing service.
- Background task routing is an explicit decision, not a default — the CMS's task layer ships
  database and RQ backends and **no Celery backend**, so inheriting the default silently splits the
  estate's task story. See `addendum.md`.

---

#### 4.3 Eight portals, one session

**Description.** Every station becomes reachable as a Lane 2 application under the one host, so an
operator moves between stations without re-authenticating or changing origin. One of eight exists
today. Realizes UJ-1.

**Functional Requirements:**

##### canopy:FR-9: All eight stations resolve behind one session

Eight portal URLs resolve, and a single authentication covers all of them. **CAP-3.**

**Consequences (testable):**
- Requesting each of the eight portals in one session triggers no re-authentication.
- All eight are same-origin with Lane 1.
- All eight mount under `/stations/<name>/`.
- The existing compliance portal is one of the eight and is not re-implemented.

##### canopy:FR-9a: The moved portal does not break its old URL

`compliance_face` relocates from `/compliance/` to `/stations/warden/` and the old path keeps
working. **CAP-3.**

**Consequences (testable):**
- `/compliance/` returns a permanent redirect to `/stations/warden/`, preserving path and query
  beneath it.
- The redirect survives as a supported route, not a temporary shim — it is not scheduled for
  removal in this chain.
- No inbound reference to `/compliance/` anywhere in the repo is left pointing at a 404.

##### canopy:FR-9b: Station portals are reusable Django apps under one naming scheme

`compliance_face` is repackaged as a reusable Django app following
[Django's reusable-app convention](https://docs.djangoproject.com/en/6.0/intro/reusable-apps/), and
that convention becomes the scheme every station's portal follows. **CAP-3.**

The triple, for warden:

| | Name |
|---|---|
| Distribution | `django-warden`, at `src/shared/packages/django-warden/` |
| Module | `django_warden_fabric` |
| App label | `warden_fabric` |

**Consequences (testable):**
- No identifier spelled `compliance_face` survives anywhere in `src/`.
- **One distribution per station, holding one or more apps** — the `django-allauth` shape. A second
  warden surface becomes a sibling app inside `django-warden`, not a second distribution.
- Every station portal's app label is `<station>_<app>`, so labels are unique across
  `INSTALLED_APPS` for any number of stations and apps, and no label collides with a Django contrib
  app.
- It installs as an in-repo path dependency — **not** a conda-forge feedstock, since it is
  first-party and never leaves the repo.
- A migration carries the app-label change: the model's table, its `django_migrations` rows and its
  `django_content_type` row all move, and applying it to a populated database preserves every
  existing job row.
- Warden's two shipped specs that name the old app still resolve — no dangling reference is left in
  `_bmad-output/projects/pyforge-warden/`.

**Notes:** Ruled 2026-08-24. **Sequencing is the whole point of putting this here.** The app carries
`label = "compliance_face"`, so renaming it is a table rename plus content-type and
migration-history updates. Today that is an ordinary Django migration. Once CAP-9 lands the
application role loses DDL rights and the same rename becomes a governed Liquibase changeset — so
this must precede §4.9, and folding it into canopy:FR-9a's move costs one disruption instead of two.

Two properties of the scheme are load-bearing and should not be simplified away later:

- **The label is `warden_fabric`, not `warden`.** A per-station label cannot survive a station
  owning a second app, and Django requires labels to be unique in `INSTALLED_APPS`. The compound
  form reserves room for `warden_baseline` beside it at no cost.
- **New concerns get new sibling apps; existing models never move between apps.** Moving a model
  later costs exactly what this FR is paying now. Adding a sibling app costs nothing. So the estate
  starts at one app per station without ever having to pay a split.

`[NOTE FOR PM]` this is the only requirement in the PRD that renames shipped, working code. It earns
its place by riding along with a move that was happening anyway; it would be hard to justify alone.

This also settles a question the PRD had left implicit: `src/shared/packages/` holds **two families
under two conventions** — station CLI/library packages (`pyforge-warden` → `pyforge.warden`, entry
point `warden = "pyforge.warden.cli:main"`) and Django reusable apps (`django-*` → `django_*`).
`django-pyforge` is correct as it stands; it is a reusable app, not a CLI package.

One editorial change followed: CAP-8's backbone was called the "event fabric" in four places, which
would have read confusingly beside `warden_fabric` in the same architecture diagram. It is now
uniformly the **event backbone**, which was already the dominant term.

##### canopy:FR-10: A portal holds no station logic

A portal renders and dispatches; the station's behaviour stays in the station. **CAP-3, CAP-6.**

**Consequences (testable):**
- A portal reaches its station only through the shared client (canopy:FR-14).
- No portal imports station internals directly.
- A test asserts no portal constructs a raw HTTP request to a service.

---

#### 4.4 Service faces for agents

**Description.** Each station exposes its capabilities to programmatic and agent callers over a
current-specification MCP endpoint, with long operations surviving connection loss. One station
(atlas) has a server today; seven do not. Realizes UJ-2.

The transport question is settled and it is not what the Dream said: the SSE transport it named is
deprecated twice over, and a compliant current server answers a GET to its endpoint with `405`.
A single POST endpoint on the official SDK is the target.

**Functional Requirements:**

##### canopy:FR-11: Eight stations answer on a current-specification endpoint

Each station exposes a service face implementing the current MCP specification. **CAP-4.**

**Consequences (testable):**
- A conformance check passes against each of the eight endpoints.
- Each endpoint accepts **`2025-03-26` through `2026-07-28`** — the four handshake revisions and
  the modern one — served from one deployment.
- An `initialize` request is answered with **the revision the client asked for**, never the
  server's own newest.
- A request declaring an unsupported revision returns `-32022` with the supported list attached,
  rather than failing opaquely.
- No code path selects behavior from the client's name or user-agent.
- The deprecated dual-endpoint SSE shape is not served.
- Atlas's existing server is brought to the same specification rather than duplicated.

**Notes:** The revision range is not a compatibility nicety — the client fleet is genuinely split.
Copilot and Zed sit at `2025-11-25`, Gemini CLI at `2025-06-18`, and Codex already sends
`2026-07-28`. Pinning either end alone rejects real traffic. Cursor's revision is unpublished, which
is itself an argument for accepting the range rather than enumerating known clients.

The echo rule earns its own consequence because the failure it prevents is counter-intuitive: a
client receiving a revision it does not recognize aborts **even when that revision is newer**.
Asserting the newest is a self-inflicted rejection, not a forward-compatible default.

##### canopy:FR-12: A long operation survives a disconnect

An operation exceeding the ingress idle timeout completes and its result is retrievable after the
client reconnects. Realizes UJ-2. **CAP-4.**

**Consequences (testable):**
- A multi-minute operation run across a simulated ingress disconnect yields its result on
  reconnection.
- The operation is not recomputed on reconnect.
- The starting call **returns without holding the connection**, proven by the response arriving well
  before the operation completes.
- The result is retrievable **from a different replica** than the one that started the work, so no
  session affinity is required.
- A handle is opaque and high-entropy, and expires — it is not a guessable or permanent identifier.
- Keep-alive interval is under 30 seconds where any stream exists at all, verified by inspecting
  emitted traffic — not by a route annotation, which is defence-in-depth only.

**Notes:** **OQ-3 is answered, and the answer removes the mechanism this FR was expected to use.**
There is no server-side Tasks runtime in the official SDK — it is listed under *Known gaps*, and the
only implementation in any language is a beta on an unreleased FastMCP 4 that conda-forge cannot
accept. So the requirement is delivered as a **`start`/`get` tool pair over a durable store**.

This is why the FR is worded as an outcome rather than a mechanism. The pair implements the same
lifecycle SEP-2663 standardizes, so adopting Tasks later is a wire-layer swap over the same store —
the durable store is the hard part, and the extension only replaces the layer above it.

Three things that look like they satisfy this FR and do not: progress notifications travel down the
live connection and die with it (they solve the spinner, not the disconnect); sticky-session
affinity is ruled out because the modern protocol revision deliberately removed sessions; and
home-grown stream replay reimplements the hard part badly. The "different replica" consequence
exists specifically to make the affinity shortcut fail its test.

`[NOTE FOR PM]` Tasks is worth a **scheduled re-check** rather than treating this as settled
forever. SEP-2663 is Final, the SDK's pluggable extension API has landed, and the tracking issue is
open to bring the extension in-repo — this could plausibly resolve during the chain.

---

#### 4.5 One command grammar

**Description.** A single entry point dispatches `pyforge <station> <noun> <verb>` to the eight
existing station CLIs without reimplementing their logic. The station binaries remain first-class;
this is a front door, not an absorption.

**Functional Requirements:**

##### canopy:FR-13: Every station verb is reachable through one entry point

`pyforge <station> <noun> <verb>` reaches the same behaviour as the station's own binary.
**CAP-5.**

**Consequences (testable):**
- A generated parity matrix lists every station verb and shows it reachable through both paths.
- The build **fails** when the two diverge — a verb added to a station CLI and not reachable
  through the unified entry point breaks CI.
- No station CLI's logic is reimplemented; dispatch only.

**Notes:** `[ASSUMPTION: the eight station CLIs expose a surface stable enough to dispatch to
without modification.]` Unverified per-station. If a station's CLI cannot be introspected for the
parity matrix, that station needs a preparatory story.

---

#### 4.6 One client, carrying identity

**Description.** Portals reach station services through a shared client that carries the end user's
identity as a signed, audience-bound assertion — not a trusted header a compromised caller could
forge. This is the seam that decides whether the estate's internal traffic is auditable, so it
lands before the portals that will use it.

**Functional Requirements:**

##### canopy:FR-14: A service can verify on whose behalf it was called

A station service independently verifies the end-user identity behind a portal call. **CAP-6.**

**Consequences (testable):**
- A service rejects a call whose assertion fails signature or audience validation.
- A service rejects an assertion minted for a different audience.
- An expired assertion is refused.
- No portal-to-service path exists that does not carry one.

##### canopy:FR-15: The trusted-header path does not exist

Identity is never asserted by an unverified header. **CAP-6.**

**Consequences (testable):**
- A request bearing an identity header but no valid assertion is refused.
- A test asserts no portal code constructs a raw request to a service.

---

#### 4.7 Analytics behind the front door

**Description.** Atlas's analytical boards become reachable through the host, with per-user row
isolation enforced at the identity boundary, adopting the estate's existing secure-dashboard
pattern rather than inventing a second one. Realizes UJ-1.

**Functional Requirements:**

##### canopy:FR-16: Two roles, same URL, different rows

Users with different roles requesting the same board receive provably different row sets.
**CAP-7.**

**Consequences (testable):**
- Two authenticated users of differing roles request one board URL; returned rows differ as their
  roles dictate.
- Isolation is enforced server-side at the identity boundary — not by client-side filtering, and
  not by serving different URLs.
- The board is reached through the Canopy, same-origin and same-session.

**Notes:** This consumes the estate's existing secure-dashboard pattern. Making atlas's own
dashboard adopt that pattern is atlas's story and explicitly out of scope here.

---

#### 4.8 Stations can tell each other things

**Description.** A durable event backbone carries structured events between stations, with consumer
groups, poison-message quarantine, and a ceiling on how deep a cascade may run. Realizes UJ-3.

**Functional Requirements:**

##### canopy:FR-17: Events are durable and consumed in groups

A published event reaches its consumers and survives a consumer restart. **CAP-8.**

**Consequences (testable):**
- An event published while a consumer is down is delivered when it returns.
- A restart reconciles rather than duplicating — reprocessing does not double-apply effects.
- The envelope carries `spec_id`, git sha, and SBOM purl, plus an optional work-item id. A
  missing Jira key does **not** fail publish or drop the event (Dream Grounding Q4).

##### canopy:FR-18: A poisoned event is quarantined, not retried forever

A message that cannot be processed lands in a dead-letter queue after its retry budget.
Realizes UJ-3. **CAP-8, CAP-10.**

**Consequences (testable):**
- A deliberately malformed event ends in the dead-letter queue.
- It does not block the consumer group.
- An operator can enumerate quarantined messages.

##### canopy:FR-19: Cascades halt at a declared depth

A cyclic publish chain stops at the declared ceiling. **CAP-8.**

**Consequences (testable):**
- A deliberately cyclic chain halts at the configured depth rather than running away.
- The halt is observable, not silent.

##### canopy:FR-20: Validation happens in the domain adapter

Event payload validation occurs in the consuming domain adapter, not at the stream boundary.
**CAP-8.**

**Consequences (testable):**
- A schema-invalid payload is rejected by the consuming adapter with a domain error.
- The stream boundary does not reject on payload shape — it is a transport, not a validator.

---

#### 4.9 Governed schema change

**Description.** Production schema change flows through one auditable authority, enforced by
**database privilege** rather than by convention, while the application's own tooling remains where
a developer authors a change. Realizes UJ-4.

This feature reopens shipped work and its literal directive turned out to be unimplementable, so
the shape below is the revised one. The framework's own bookkeeping — content types, permissions,
sites — has exactly one supported population mechanism, and the test runner builds every test
database by running migrations. So migrations keep running; what changes is who is allowed to
execute DDL. That is also the only version of this an auditor can verify, which is the point.

**Functional Requirements:**

##### canopy:FR-21: Liquibase is available inside the boundary

The governed-changeset tool resolves from conda-forge like every other Python/pixi dependency.
**CAP-9.**

**Consequences (testable):**
- A recipe exists and builds at **5.0.4 or later**; the tool is available in the platform
  environment.
- The PostgreSQL JDBC driver is **vendored into the recipe** — recent Community releases stopped
  bundling it and the package manager fetches it over the network, which an air gap forbids.
- No new container image is introduced.
- A `runInTransaction="false"` changeset applied against a non-default schema lands in that schema,
  demonstrated against a live PostgreSQL instance.

**Notes:** Per repo Rule 1, this story's dev session invokes `conda-forge-expert`. This FR **gates
the rest of §4.9** — the epic opens with packaging work, not platform work.

The version floor is not arbitrary. 5.0.2 and 5.0.3 carry a defect where `SET LOCAL SEARCH_PATH`
is a no-op outside a transaction, so non-transactional changesets silently resolved in the wrong
schema; it is fixed in 5.0.4. Separately, 5.0.4 is the **first release whose GPG signature verifies
against the rotated signing key**, which decides the recipe's verification step. The last
consequence exists because the fix is currently verified by a reviewer's report rather than by our
own observation — cheap to close, and CAP-9 rests on it.

##### canopy:FR-21a: Schema resolution cannot fail silently

Schema targeting is configured so that a misresolution is impossible rather than merely unlikely.
**CAP-9.**

**Consequences (testable):**
- `preserveSchemaCase` is disabled and no schema name is mixed-case — a check fails if either
  changes.
- The connection carries its own schema targeting rather than relying on the tool's search-path
  manipulation.
- The pre-upgrade Job connects directly to PostgreSQL, not through a transaction-pooling proxy.

**Notes:** `[NOTE FOR PM]` this FR exists because of an **open, unfixed** upstream issue: with
`preserveSchemaCase` enabled the schema name is double-quoted into one that does not exist, and DDL
then applies silently to `public`. Silent wrong-schema DDL is the worst available failure mode for
this feature, and the mitigation costs nothing because Django's naming conventions already produce
lowercase. Do not let a later story turn this flag on for a formatting reason.

##### canopy:FR-22: The application role cannot alter its own schema

The role the application connects with holds no DDL privilege. Realizes UJ-4. **CAP-9.**

**Consequences (testable):**
- `CREATE`, `ALTER` and `DROP` attempted as the application role are refused **by the database**.
- A separate migration role holds DDL and is used only by the governed step.
- The refusal is a privilege error from PostgreSQL, not an application-level guard.

##### canopy:FR-23: A schema change without a governed changeset fails the build

Authoring a model change without its corresponding changeset breaks CI. **CAP-9.**

**Consequences (testable):**
- A model change with no matching changeset fails a check.
- The check names the missing changeset.

**Notes:** `[NOTE FOR PM]` No prior art exists for this — no team is documented running Liquibase as
schema authority for a Django application. Size this as invention, not integration.

##### canopy:FR-24: The deploy sequence keeps framework bookkeeping working

The governed step runs before the application's migration step, and the latter still fires
framework post-migration hooks. **CAP-9.**

**Consequences (testable):**
- The governed changeset applies as a pre-upgrade hook Job at a lower hook-weight than the existing
  migration Job, on the same platform image.
- The existing migration Job still runs, so content types, permissions and sites are populated.
- **No init container is introduced** — replicas would contend on the changelog lock, and the
  shipped Job's own documentation records that waiting on hooks deadlocks migration-gated
  readiness.
- The chart contract from the shipped story is not rewritten; this is a seam beside it.

##### canopy:FR-25: Test databases are carved out

The governed authority does not apply to test databases. **CAP-9.**

**Consequences (testable):**
- The test runner continues to build databases by running migrations, unchanged.
- No test-suite change is required by this feature.

---

#### 4.10 Containment

**Description.** A failing dependency degrades its caller instead of cascading; concurrent writers
cannot corrupt shared analytical state; validation errors reach the user inline; a restart
reconciles rather than duplicates. And the queue and the cache stop being able to evict each other.

Each invariant is demonstrated **individually** — a test that fails with the invariant absent and
passes with it present. A suite that goes green proves nothing about any one of them.

**Functional Requirements:**

##### canopy:FR-26: A failing dependency degrades its caller

A dependency failing repeatedly opens a circuit and the caller degrades rather than hanging.
**CAP-10.**

**Consequences (testable):**
- Repeated failures open the circuit; the caller returns a degraded response within its budget.
- **The async path trips correctly** — a failing asynchronous call registers as a failure, not a
  success.
- Removing the containment makes the test fail.

**Notes:** The chosen library's async support targets a different coroutine model; an asynchronous
client call passed to it registers a false success and the circuit never trips. A thin wrapper is
required and is a known, sized piece of work — see `addendum.md`. `[ASSUMPTION: its cross-replica
state transitions are not atomic]`, read from source rather than documentation, so the failure
threshold is coarse protection and not exact-count semantics. Do not write an FR that depends on an
exact count.

##### canopy:FR-27: Concurrent writers cannot corrupt shared analytical state

A single-writer boundary is enforced for the columnar analytical store. **CAP-10.**
CAP-19 names that store as the **query plane** (canopy:FR-27 *intent* survives if the
file is no longer literally `atlas.duckdb`).

**Consequences (testable):**
- A second concurrent writer is refused or serialized; no corruption occurs.
- The test fails if the boundary is removed.

##### canopy:FR-28: Validation errors reach the user inline

A validation failure is rendered in place rather than lost or thrown as an opaque error.
**CAP-10.**

**Consequences (testable):**
- A rejected submission renders its errors inline in the originating surface.
- The test fails if the inline path is removed.

##### canopy:FR-29: A restart reconciles rather than duplicates

Work interrupted by a restart is reconciled, not re-applied. **CAP-10, CAP-8.**

**Consequences (testable):**
- An operation interrupted mid-flight and resumed produces one effect, not two.
- The test fails if reconciliation is removed.

##### canopy:FR-30: Queue and cache cannot evict each other

Broker and cache are separate resources with separate eviction policies. **CAP-11.**

**Consequences (testable):**
- Filling the cache to its eviction limit **provably loses no queued task**.
- The broker's eviction policy refuses to evict; the cache's evicts by recency.
- Web and worker pools scale independently.

---

#### 4.11 Access, secrets, and flags

**Description.** Authorization derives from identity-provider roles rather than locally-managed
state; runtime secrets arrive from a secret manager rather than the pod environment; and behaviour
flips without a redeploy through one vendor-neutral flag interface evaluated entirely offline.
Realizes UJ-5.

**Functional Requirements:**

##### canopy:FR-31: Revoking a role at the IdP removes access

A role revoked centrally takes effect on the user's next request. **CAP-12.**

**Consequences (testable):**
- Revoking the role at the IdP denies portal access on the next request — not at next login, and
  not after a cache expiry.
- Local group state is not the authority.

##### canopy:FR-32: No long-lived secret appears in a pod specification

Runtime secrets are delivered by a secret manager. **CAP-12.**

**Consequences (testable):**
- No secret value appears in any pod specification or chart value.
- A check over rendered manifests fails if one does.

##### canopy:FR-33: Flag packages are available inside the boundary

The flag interface and its provider resolve from conda-forge. **CAP-13.**

**Consequences (testable):**
- Four new feedstocks exist and build: `openfeature-sdk`, `openfeature-flagd-api`,
  `openfeature-flagd-core`, `openfeature-provider-flagd`.
- A `cachebox` 5.x build exists — conda-forge ships 6.2.5 and the provider pins `<6`.
- The version conflict is resolved by that build rather than pinned around silently.

**Notes:** The four OpenFeature packages are absent from anaconda.org **entirely** — a global
search returns zero results. `cachebox` is a different task: the feedstock exists at the wrong
version, so it is a **downgrade build, not a new recipe**, and sizing it as a fifth new recipe
overstates it. Per repo Rule 1 each of these stories invokes `conda-forge-expert`. Like canopy:FR-21, this
FR **gates the rest of its feature**.

##### canopy:FR-34: One flag flips three surfaces, offline

A single flag change alters behaviour across web, service and CLI. Realizes UJ-5. **CAP-13.**

**Consequences (testable):**
- One flag change is observed by all three surfaces.
- No egress occurs during evaluation — evaluation is in-process from a local source.
- No redeploy and no restart is required.

---

#### 4.12 Scribe's graph outlives one file

**Description.** The knowledge graph gains a durable, concurrent-safe backing store behind its
existing port, keeps a local-development path, and gains semantic recall. Today it is one flat JSON
file — the Dream's premise of an existing dual-driver engine was simply wrong, so this is a first
driver, not a second.

**Functional Requirements:**

##### canopy:FR-35: The same operations pass against both drivers

Graph operations behave identically against the durable store and the local path. **CAP-14.**

**Consequences (testable):**
- One operation suite passes against both drivers.
- The existing port is unchanged — callers are unaware which driver is active.
- Concurrent writers do not corrupt the durable store.

##### canopy:FR-36: Semantic recall returns what lexical recall cannot

Recall finds a semantically relevant result that token-overlap search misses. **CAP-14.**

**Consequences (testable):**
- A query with no lexical overlap with its target returns that target.
- The same query under the lexical path does not.

---

#### 4.13 The agent-facing tiers

**Description.** The Dream promises five-tier symmetry — CLI, portal, service, domain skill,
persona — as the **03 shape of each of the eight stations**. That gap was the 2026-08-24
motive: one domain skill of eight and zero station personas. **2026-08-26 (Epic 37.1):**
the check reports **40/40**; mason's skill cell is `conda-forge-expert` (no
`pyforge-mason/` skill). 01/02 work does not owe this matrix. Fewer-than-five on an
**03 capability** remains a contract violation — the check now fails CI on a missing cell.

**Functional Requirements:**

##### canopy:FR-37: Each station carries a domain skill

Every **03** station has an agent-loadable skill encoding how its work is actually done. **CAP-15.**

**Consequences (testable):**
- An agent asked to perform a station's core task loads that station's skill and follows it.
- Demonstrated for a station that has **no** skill today — not for the one that already does.
- Each skill follows the shape the existing one proves.

##### canopy:FR-38: Each station is addressable as a persona

Every **03** station exposes a persona that acts only through that station's grammar and service
face. **CAP-16.** 01/02 work does not mint a persona.

**Consequences (testable):**
- A persona completes a station task end to end.
- Its transcript shows **no** direct filesystem access and **no** ad-hoc HTTP calls — only canopy:FR-13's
  grammar and canopy:FR-11's service face.

##### canopy:FR-39: Five-tier completeness is checkable

**03** station completeness is mechanically verifiable, not asserted. **CAP-15, CAP-16.**

**Consequences (testable):**
- A check enumerates all eight **03** stations across all five tiers and reports which are missing.
  Denominator remains 8 × 5 = 40.
- The check fails when an **03** station is declared complete with fewer than five.
- The check does **not** fail 01/02 work for lacking a portal, service, skill, or persona.

---

#### 4.14 Run state is a service

**Description.** In-flight execution state — which runs are live, how long they have been going,
and the timing history behind them — is published by a supervisor the front door can query, rather
than read off an operator's local disk when a static page is generated.

This feature exists because of a decision, not a discovery. The parity inventory found that three
of the retired console's surfaces read `~/.bmad-loops`, tmux sessions and journal files directly,
which is why the published board showed `unavailable` for all of them. The inventory recommended
dropping those surfaces; the operator chose on 2026-08-24 to keep them and pay for the service that
makes them deployable. **The replacement is therefore held to a higher bar than the thing it
replaces**, and that is deliberate.

**Functional Requirements:**

##### canopy:FR-40: Live run state is queryable, not scraped

The front door obtains run state from a service. **CAP-17.**

**Consequences (testable):**
- Live run state renders in a deployed namespace with **no access to any operator home directory**
  — the deciding test, because it is exactly what fails today.
- No front-door code path reads a filesystem for run state, and no fallback to scraping exists.
- A run started on one machine is visible to a front door running on another.

##### canopy:FR-41: A run's timing survives the workstation that produced it

Completed-run timing is ingested into durable storage rather than left in a local journal.
**CAP-17.**

**Consequences (testable):**
- A run's timing is retrievable after its originating workstation is unavailable.
- Ingestion happens at run completion, not at page-generation time.
- Timing history is queryable across runs, not only for the most recent.

##### canopy:FR-42: The supervisor degrades honestly

When the supervisor is unreachable, the surface says so rather than implying staleness is
liveness. **CAP-17, CAP-10.**

**Consequences (testable):**
- An unreachable supervisor renders an explicit unavailable state, not an empty list and not stale
  data presented as current.
- Any displayed run state carries its age.
- The front door does not hang waiting on the supervisor — it degrades within its budget, per
  canopy:FR-26.

**Notes:** `[NOTE FOR PM]` this feature was added after the capability set was otherwise settled,
and it is the one place this chain grew rather than converged. It is worth a deliberate look during
the readiness gate: it is genuinely useful, and it is also the kind of scope that arrives late and
is not sized with the same rigor as the rest.

---

#### 4.15 One plugin API, then Warden, then station processes

**Description.** Canopy Epics 18–30 mount chrome, portals, MCP, events, and DDL. They do not
extract replaceable layers. **CAP-18** is the missing story: one hook-spec plus plugin-registration
shape in `pyforge-core` so eight stations do not invent eight APIs. Warden is the first concrete
retrofit (PR-gate hook specs; current scanners become optional plugins; default Warden stays green
with no Checkmarx). Each station's package then extracts its process layer (build engine, runner,
store, exporter, deploy profile, LLM provider); today's backend is the default plugin.

**Functional Requirements:**

##### canopy:FR-43: Shared hook-spec and plugin registration

`pyforge-core` publishes one registration API and one documentation shape for hook
specifications. Station packages consume it; they do not ship a second plugin loader.
**CAP-18.**

**Consequences (testable):**
- A dummy plugin loads through the shared API.
- A conformance check **fails** if a station package introduces a parallel registration
  mechanism for the same class of extension.
- Named hook points are before / after / around (or an equivalent documented set). A plugin
  must not publish a second verdict for a process another owner specified.

##### canopy:FR-44: Warden owns PR-gate hooks; scanners are optional plugins

Warden owns the PR-gate hook specifications on the canopy:FR-43 contract. Existing scanners become
plugins. A missing named scanner (including Checkmarx) is not a failed Warden run.
**CAP-18.** Q8.

**Consequences (testable):**
- Default Warden / CI invocation is green with no named commercial scanner plugin installed.
- Enabling an optional scanner plugin can change findings; it cannot replace the Warden verdict
  with a second pass/fail published beside it.

##### canopy:FR-45: Each 03 station extracts one process hook spec

Each 03 station identifies a replaceable process layer, publishes a hook spec on the canopy:FR-43
contract, and registers today's backend as the default plugin. Atlas **audits** existing Kedro
hooks against the contract; it does not rebuild the pipeline or grow a pipeline PR-gate.
**CAP-18.**

**Consequences (testable):**
- Swapping the vendor/backend for that layer does not require forking the station process.
- Steward deploy-profile adapters (Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, Jira) are
  plugins on this FR, not core stack.

**Notes:** Order is canopy:FR-43, then canopy:FR-44, then canopy:FR-45 on the next process change (Warden first).
Epics 18–30 must not violate CAP-18; they are not its implementation.

---

#### 4.16 The query plane (CAP-19)

Stations stop inventing stores. One DuckDB engine federates live Postgres (read-only),
serves Kedro Parquet, and ranks vectors. Agents do not get the OLTP DSN. Rebuild of
Atlas RAG defaults, Scribe semantic recall, and Langflow/DB-GPT estate reads is
authorized. Realizes UJ-6.

##### canopy:FR-46: Live federation is read-only attach

DuckDB attaches a multi-schema Postgres as `READ_ONLY`. No `pgvector` is required on
that database. **CAP-19.**

**Consequences (testable):**
- A fixture with two schemas answers a federated `SELECT` through the plane.
- A write against the attach is refused.
- The test fails if the path goes through pandas SQL or a writable attach.

##### canopy:FR-47: Analytical scans hit the Parquet cache

Kedro writes compressed Parquet on a named catalog pipeline. Dashboards and
autonomous SQL read the cache, not OLTP. **CAP-19.**

**Consequences (testable):**
- After `kedro run` of the named pipeline, the cache file exists and a query
  against it does not open the OLTP writer role.
- The test fails if Airflow or an `01_raw` tree is the refresh mechanism.

##### canopy:FR-48: Vectors live on the plane

`REAL[]` (or equivalent) casts to `FLOAT[N]` and HNSW / `vss` ranking runs in
DuckDB SQL. Dimension is a parameter. Consumer `LOAD`s `vss`. **CAP-19.**

**Consequences (testable):**
- Nearest-neighbor returns the planted row without lexical overlap.
- The consumer path does not `INSTALL` on the network.
- The test fails if a second writable `.duckdb` file is the index home.

##### canopy:FR-49: Agents cannot use the OLTP DSN

DB-GPT Text-to-SQL and Langflow estate RAG are configured at the plane (cache,
declared views, or the HTTP/Arrow face). **CAP-19.**

**Consequences (testable):**
- Config/tests show the estate read DSN is the plane, not `langflow_schema` /
  enterprise OLTP.
- A mis-aimed OLTP DSN for Text-to-SQL fails the gate.

##### canopy:FR-50: Stations reimplement onto the plane

Scribe semantic recall uses `GraphStore.query_similar` backed by the plane (or a
driver that is the plane). Atlas RAG persist uses the plane writer. BSL remains
the dashboard contract. **CAP-19.** Rebuild of 28.2 / in-memory RAG is in scope.

**Consequences (testable):**
- canopy:FR-36 still holds after the Scribe path moves.
- Callers do not `isinstance` the driver.
- The test fails if semantic recall is aliased back to lexical or to a private
  Chroma / in-memory DuckDB.

---

### 5. Non-Goals (Explicit)

- **Not a rewrite of the host.** `src/platform/` stands. No rename, no relocation of `config/` or
  `platformapp/`.
- **Not a ninth station or a ninth project.** The roster stays at eight.
- **Not a re-decision of the monolith-versus-microservices topology.** That trail is closed
  elsewhere and reopening it is out of scope.
- **Not a replacement for any station CLI.** canopy:FR-13 dispatches; station binaries remain first-class.
- **Not atlas's own Wagtail Spec.** CAP-2 may end up serving one of its waiting consumers (OQ-5),
  but does not absorb, re-mint or supersede it.
- **Not CodeRed CMS.** Ruled out on maintenance evidence.
- **Not a general-purpose multi-tenancy model.** canopy:FR-16 is row isolation for boards, nothing more.
- **Not atlas's adoption of the secure-dashboard pattern.** Consumed here; adopting it in atlas's
  own board is atlas's story.
- **Not an external API contract.** The service faces are for estate callers; no third-party
  versioning promise.

### 6. MVP Scope

MVP here means "the smallest cut where the estate behaves as one system", not "the first
demonstrable slice". Two features are excluded from it for opposite reasons — one because it is
gated on external packaging, one because it is a migration that should not be rushed.

#### 6.1 In Scope

- Shared chrome (canopy:FR-1..canopy:FR-3) — everything visual depends on it.
- Eight portals behind one session (canopy:FR-9, canopy:FR-10).
- The identity-carrying client (canopy:FR-14, canopy:FR-15) — before its consumers, or the first integration
  becomes a trusted header nobody removes.
- Service faces on a current specification (canopy:FR-11), with resumability (canopy:FR-12) as the risk item.
- One command grammar (canopy:FR-13).
- Queue/cache separation (canopy:FR-30) — cheap, and it prevents a whole class of production surprise.
- IdP-derived authorization and delivered secrets (canopy:FR-31, canopy:FR-32).

#### 6.2 Out of Scope for MVP

- **Governed schema change (§4.9)** — gated on a feedstock, reopens shipped stories, and has no
  prior art. Deferring it does not weaken the MVP's demonstration; rushing it risks the estate's
  database.
- **Flags (§4.11 canopy:FR-33, canopy:FR-34)** — gated on four absent feedstocks plus a downgrade build.
  `[NOTE FOR PM]` this is the one deferral most likely to be regretted, because flags would
  de-risk every other rollout in the chain. If packaging lands early, pull it forward.
- **Lane 1 supersession (§4.2)** — the front door itself is MVP-adjacent, but retiring the console
  is a migration with a parity precondition. The build may land in MVP; **the removal may not**.
- **Semantic recall (canopy:FR-36)** — durability (canopy:FR-35) is the urgent half of CAP-14.
- **Personas (canopy:FR-38)** — depend on canopy:FR-13 and canopy:FR-11 both existing first.

### 7. Success Metrics

**These are stated as binary gates, not as targets, and that is deliberate.** No baseline
measurement exists for this estate — no current-state latency, adoption or incident numbers — so a
percentage target here would be invented, and an invented target propagates into an acceptance
criterion nobody can evaluate. Where a number appears below it is a threshold already fixed by an
external constraint, not a goal we chose.

**Primary**

- **SM-1 — One session spans the estate.** An operator traverses Lane 1 → a station portal → an
  analytical board with a single authentication and no origin change. Binary. Validates canopy:FR-4, canopy:FR-9,
  canopy:FR-16.
- **SM-2 — An agent survives the proxy.** A multi-minute operation completes across a simulated
  ingress disconnect and its result is retrieved. Binary. Validates canopy:FR-11, canopy:FR-12.
- **SM-3 — The application cannot alter its own schema.** `CREATE`/`ALTER`/`DROP` as the
  application role are refused by PostgreSQL. Binary, and verifiable by an auditor without reading
  application code. Validates canopy:FR-22.
- **SM-4 — The egress-blocked deploy succeeds.** A build and deploy with external egress blocked
  completes end to end, carrying only PostgreSQL, Redis and the platform images. Binary; already
  the estate's existing gate. Validates canopy:FR-21, canopy:FR-33, and the air-gap constraint generally.
- **SM-5 — Five tiers, eight 03 stations.** The completeness check reports all eight **03**
  stations with all five tiers present. Countable, with a known denominator: 8 × 5 = 40.
  01/02 work is outside the denominator. Validates canopy:FR-37, canopy:FR-38, canopy:FR-39.

**Secondary**

- **SM-6 — Each containment invariant fails without itself.** Each of the four invariants has a
  test demonstrated individually to fail when the invariant is removed. Count: 4 of 4. Validates
  canopy:FR-26..canopy:FR-29.
- **SM-7 — Chrome is not duplicated.** The duplication check finds zero portal-local copies of
  chrome. Count: 0. Validates canopy:FR-1.
- **SM-8 — CLI parity holds.** The generated matrix shows every station verb reachable both ways,
  and CI fails on divergence. Validates canopy:FR-13.
- **SM-9 — One plugin API.** A dummy plugin loads through `pyforge-core`; a station-local second
  registration API fails the check; default Warden is green with no named commercial scanner.
  Validates canopy:FR-43, canopy:FR-44, canopy:FR-45.

**Counter-metrics (do not optimize)**

- **SM-C1 — Do not optimize portal count.** Eight portals that render but hold station logic is a
  worse outcome than six that are properly thin. Counterbalances SM-1; enforced by canopy:FR-10.
- **SM-C2 — Do not optimize event throughput.** The backbone's value is durability, ordering and
  quarantine. A faster backbone that drops or double-applies has failed. Counterbalances the CAP-8
  work; enforced by canopy:FR-17, canopy:FR-18, canopy:FR-29.
- **SM-C3 — Do not optimize for the skill/persona count.** Eight shallow skills that no agent
  actually follows satisfies SM-5 and delivers nothing. Counterbalances SM-5; enforced by canopy:FR-37's
  "demonstrated for a station that has no skill today".
- **SM-C4 — Do not optimize migration speed.** canopy:FR-23's build gate will slow schema authoring. That
  cost is the feature. Counterbalances SM-3.

### 8. Cross-Cutting NFRs

- **Air-gap.** Every Python/pixi dependency resolves from conda-forge; the egress-blocked build is
  a gate, not a warning. Container images are governed separately by the platform Spec's
  internal-registry rule. Both boundaries bind; neither substitutes for the other.
- **Backing services.** Exactly PostgreSQL, Redis and Kubernetes. A component demanding a fourth
  has failed design review. DuckDB is a library / optional query face on the platform image,
  not a fourth Helm kind (CAP-19).
- **Statelessness.** Replicas are capacity; any pod is disposable. This rules out pod-local media
  (canopy:FR-8) and per-process caches.
- **Runtime floor.** Django `>=5.2.15,<6` and Python `3.12.*`. Zero headroom — conda-forge ships
  exactly one qualifying build, two **security** patch releases behind upstream. Audited
  2026-08-24: seven CVEs across 5.2.16 and 5.2.17, one rated high, and **every affected path is
  unreachable here**. A currency gap rather than a live exposure — but the pin should still move to
  `>=5.2.17,<6`, because scanners key on version strings rather than reachability and an SBOM
  declaring seven unremediated CVEs is a finding whatever the analysis says. The feedstock's `5.x`
  maintenance branch exists and this repo's maintainer has bumped it before, so this is a one-file
  PR, not chain scope.
- **Import boundary.** `src/platform/` consumes the factory's published conda packages and never
  imports factory source.
- **Ingress timing.** Any long-lived response keeps alive well under 30 seconds. The platform's
  router timeout is cluster-wide with no per-route override; a route annotation is
  defence-in-depth, never the mechanism.

### 9. Constraints and Guardrails

**Sequencing constraints** — facts about the work, not preferences. Each dictates ordering, and the
epic pass must honour rather than rediscover them.

1. **Packaging precedes platform in two features.** canopy:FR-21 gates §4.9; canopy:FR-33 gates canopy:FR-34. Both
   epics open with `conda-forge-expert` sessions.
2. **canopy:FR-1 precedes canopy:FR-4 and canopy:FR-9.** Chrome first, or portals grow their own.
3. **canopy:FR-14 precedes canopy:FR-9's integrations.** The client before its consumers.
4. **canopy:FR-6 precedes canopy:FR-7.** Inventory before removal, unconditionally.
5. **canopy:FR-13 and canopy:FR-11 precede canopy:FR-38.** A persona has nothing to act through otherwise.

6. **The inventory (canopy:FR-6) precedes the parity build, which precedes the removal (canopy:FR-7).** Three
   stories, in that order. The inventory is done; the removal carries the 100+ reference sweep and
   the spec correction, and must not start until the parity build proves the reproducible surfaces.
7. **Phase 5 is eight `bmad-correct-course` runs, not one** — one per station, recording each
   station's Canopy obligations, with Marshal's additionally retiring `spec-factory-console`. That
   skill, not the epic pass, also decides the ledger shape for reopening the two `done` stories
   canopy:FR-22 contradicts: a new superseding epic, or a reopened Epic 11.

**Change-management guardrail.** §4.2 removes something that works today. The guardrail is canopy:FR-6's
inventory as a hard precondition and canopy:FR-7's requirement that removal be real. A "temporarily keep
both" outcome is the failure mode to guard against — it is how a supersession becomes a permanent
second console.

**Audit guardrail.** canopy:FR-22 is deliberately enforced at the database rather than in application
code, because a control an auditor can verify without reading source is worth more than a stricter
control they cannot.

### 10. Integration and Dependencies

- **Identity provider** — OIDC, already live. canopy:FR-5, canopy:FR-31 and the CAP-6 assertion chain all depend
  on it. Group/claim mapping for CMS admin (canopy:FR-5) is **new work with no first-party guidance**.
- **The shipped chart** — canopy:FR-24 adds a Job beside the existing migration hook, on the same image.
  The existing chart contract is not rewritten.
- **The existing compliance portal** — becomes one of the eight (canopy:FR-9). URL scheme is bound:
  `/stations/<name>/` with `/compliance/` redirect (canopy:FR-9a). OQ-4 is answered.
- **Atlas's MCP server** — brought to the current specification by canopy:FR-11 rather than duplicated.
- **Atlas's waiting CMS consumer** — OQ-5 / `lane1-serves-dw-h3` **answered 2026-08-25: no.**
  Host Wagtail `/cms/` does not satisfy `LaSuiteClient` Docs REST. DW-H3 stays atlas.
- **Packaging (canopy:FR-21, canopy:FR-33)** — operator-owned conda-forge recipes (canopy:AD-16; Stories 26.3
  and 27.1 stay blocked). Not in-chain CFE sessions for Canopy implementation.

### 11. Open Questions

**Still open:** none.

**Answered 2026-08-25:**

1. ~~**Can Lane 1 serve atlas's waiting consumer?** (`lane1-serves-dw-h3`)~~ — **no.** Atlas's
   shipped `LaSuiteClient` froze La Suite Docs REST (`POST /api/v1/documents/` etc.), which is
   *not* host Wagtail `/cms/`. Epic 20 (Lane 1 exists) is independent. This chain does not
   absorb `spec-wagtail-corporate-brain`. DW-H3 stays atlas attended bring-up.

**Answered 2026-08-24:**

-3. ~~**MCP runtime base (FastMCP vs official `mcp` SDK)**~~ — **hybrid, canopy:AD-5.** Service
   faces on the host are the official `mcp` SDK (`>=2.0.0`) on the one ASGI process. Stopgap in
   `local-recipes` only: `fastmcp >=3.4.7,<4` + `mcp >=1.24,<2.0` until those faces land; lift the
   `mcp` ceiling in the canopy:FR-11 story. The pairing outage is contained, not reopened.
-4. ~~**One Liquibase tracking schema or one per application?**~~ — **one tracking schema**,
   canopy:AD-9: `liquibaseSchemaName=liquibase`. Four PostgreSQL schemas in this instance
   (`public`, `langflow_schema`, `dbgpt_schema`, `liquibase`). A fifth schema is a review-blocking
   finding. Concurrent migrate of two applications shares that global changelog lock; that is
   the bound cost.

-2. ~~**MCP client revision**~~ — **accept `2025-03-26` through `2026-07-28`**, which `mcp` 2.0.0
   already serves dual-era with no configuration. The fleet is split (Copilot and Zed at
   `2025-11-25`, Gemini CLI at `2025-06-18`, Codex already at `2026-07-28`), so both ends are load
   bearing. Bound into canopy:FR-11, along with two invariants the research surfaced: echo the client's
   requested revision, and never branch on client name.
-1. ~~**MCP resumable-operation runtime**~~ — **no, and blocked upstream.** The Tasks extension is
   listed under the SDK's *Known gaps*; the only runtime in any language is a beta on an unreleased
   FastMCP 4, absent from conda-forge along with its own dependency. canopy:FR-12 ships a `start`/`get`
   pair over a durable store instead — the same lifecycle SEP-2663 standardizes, so adopting it
   later is a wire-layer swap. Worth a scheduled re-check rather than treating as closed.
0. ~~**Liquibase multi-schema regression**~~ — **fixed in 5.0.4**, corroborated by both the merged
   PR and the release notes. The question was framed too broadly: the defect only affected
   `runInTransaction="false"` changesets, never in-transaction ones. It surfaced a worse hazard in
   its place — an **open** issue where `preserveSchemaCase` causes DDL to land silently in
   `public` — now bound as canopy:FR-21a.

5. ~~**Portal URL scheme**~~ — **uniform `/stations/<name>/` for all eight**, with
   `compliance_face` moving from `/compliance/` behind a permanent redirect. One rule beats eight
   exceptions, and the registration seam enforces it (canopy:FR-2, canopy:FR-9, canopy:FR-9a). The cost is a migration
   of a shipped URL, which the redirect absorbs.
6. ~~**Django patch-level exposure**~~ — **audited 2026-08-24: a currency gap, not an exposure.**
   5.2.16 and 5.2.17 are both security releases carrying seven CVEs, one rated high — and every
   affected path is unreachable here. The premise underneath the question was also wrong: the
   feedstock's `5.x` maintenance branch **does** exist and this repo's maintainer has already
   bumped it, so moving the pin to `>=5.2.17,<6` is a one-file PR rather than the seventh packaging
   item it was sized as. Recommended, not required: scanners read version strings, not
   reachability.
7. ~~**Console parity classification**~~ — answered by the canopy:FR-6 inventory, and the question it
   raised in turn is **also** answered: live run state and journal-derived timing **stay on the
   front door**, which means building the supervisor that makes them deployable. That is
   **CAP-17 / §4.14**, new scope taken deliberately.

8. **Query plane face / catalog / Scribe cutover** — still open on the SPEC as
   `query-plane-face`, `query-plane-catalog`, `query-plane-scribe-cutover`.
   Defaults held through Epic 34: in-process first; named new Atlas pipeline;
   store-port driver on the plane (**34.5 shipped the driver**). Residual is
   Mosaic-as-required vs optional, catalog naming, and whether to retire
   `scribe_schema` pgvector. Do not re-dispatch 34.1.

### 12. Traceability

Every capability has at least one FR; every FR names a capability.

| CAP | FRs | CAP | FRs |
|---|---|---|---|
| CAP-1 | canopy:FR-1, canopy:FR-2, canopy:FR-3 | CAP-10 | canopy:FR-18, canopy:FR-26..canopy:FR-29, canopy:FR-42 |
| CAP-2 | canopy:FR-4..canopy:FR-8 | CAP-11 | canopy:FR-30 |
| CAP-3 | canopy:FR-2, canopy:FR-9, canopy:FR-9a, canopy:FR-9b, canopy:FR-10 | CAP-12 | canopy:FR-3, canopy:FR-5, canopy:FR-31, canopy:FR-32 |
| CAP-4 | canopy:FR-11, canopy:FR-12 | CAP-13 | canopy:FR-33, canopy:FR-34 |
| CAP-5 | canopy:FR-13 | CAP-14 | canopy:FR-35, canopy:FR-36 |
| CAP-6 | canopy:FR-10, canopy:FR-14, canopy:FR-15 | CAP-15 | canopy:FR-37, canopy:FR-39 |
| CAP-7 | canopy:FR-16 | CAP-16 | canopy:FR-38, canopy:FR-39 |
| CAP-8 | canopy:FR-17..canopy:FR-20, canopy:FR-29 | CAP-17 | canopy:FR-40, canopy:FR-41, canopy:FR-42 |
| CAP-9 | canopy:FR-21, canopy:FR-21a, canopy:FR-22..canopy:FR-25 | CAP-18 | canopy:FR-43, canopy:FR-44, canopy:FR-45 |
| CAP-19 | canopy:FR-46, canopy:FR-47, canopy:FR-48, canopy:FR-49, canopy:FR-50 | | |

### 13. Assumptions Index

- **§4.5 canopy:FR-13** — the eight station CLIs expose a surface stable enough to dispatch to without
  modification. Unverified per-station; a station that cannot be introspected needs a preparatory
  story.
- **§4.10 canopy:FR-26** — the circuit breaker's cross-replica state transitions are not atomic. Read from
  source, not documentation. Consequence: no FR may depend on an exact failure count.
- **§4.2** — Marshal's console views are re-creatable as CMS pages plus portal routes. Under test
  by the canopy:FR-6 inventory; a build-time-only view forces a scope conversation.
- **§2** — the agent is a first-class user, weighted equally with the three human roles. Derived
  from the capability set rather than from a stated requirement.

### 14. What Comes Next

Architecture spine and Canopy Epics **18–30** already exist. First Canopy dispatch remains
**S-18.1** (chrome). **CAP-18** is a later-day bind: steward **Epic 32** (shared contract in
`pyforge-core`, then steward deploy-profile plugins), **Warden Epic 9** (PR-gate retrofit),
then each station's process-hook story. Do not regenerate the whole steward sprint feed
(slug truncation). Packaging stays operator-owned (S-26.3, S-27.1). Scorecard remains a
sibling Dream — CAP-18 is **not** that board.

**2026-08-26 first slice shipped:** Epic 34.1–34.5, 35.1 (sibling MCP CAP-4),
36.1–36.2, 37.1. SPEC stays `ready` for the three CAP-19 OQs — do not
re-dispatch 18–37. `django-lasuite` is not a Canopy FR. Mosaic
`duckdb-server` stays optional until `query-plane-face` is answered.
MCP slice 3 (retire ImportError skip) stays parked.

**2026-08-31 reconciliation (chain-currency sweep, brief refresh):** re-derived against the brief's
2026-08-31 update, which folded in `technical-pyforge-station-dossier-2026-08-30.md` (fleet-wide,
all eight stations plus `pyforge-core`). No FR, CAP, or scope change — the dossier corroborates
rather than contradicts: canopy:FR-43..45's CAP-18 hook-spec is confirmed already live in `pyforge-core`
today (`core.hooks`, one entry-point group) and used by all seven non-core stations with no
station-specific alternative, and the doc-drift pattern it found (Marshal's skill documents 4 of
~40 commands, Doctor's and Steward's READMEs understate their real duty/story count, Scribe's
README self-contradicts) is further evidence for the §1 Vision problem this PRD already targets,
not new scope.

**2026-09-02 correct-course (red-team CRITICALs):** the adversarial review found the CAP-6
mint root unverified (X-1) and the CAP-11 broker volatile and unbounded (S-1). Steward
**Epic 40** (40.1 verified mint, 40.2 durable bounded broker) dispatches **before** any
further story on this chain and before cutover Phase 1. No FR changes; canopy:FR-30's consequence
now also reads "a broker restart loses no queued task". The review's HIGH set is a later
correct-course. Record: `sprint-change-proposal-2026-09-02-red-team-critical.md`.

**2026-09-02 correct-course (red-team HIGH set):** Epics **41–43** (fourteen stories) bind
R-3 … R-16; R-17 … R-25 sit in the deferred-work ledger as `DW-RT-2026-09-02-*`. No FR
changes; SPEC Constraints gained a dated Always/Never block. Order 40 → 41 → 42 → 43, all
before cutover Phase 1. Record: `sprint-change-proposal-2026-09-02-red-team-high.md`.

**2026-09-09 correct-course (currency review):** Epics **48–49** (sixteen stories) bind the
review's residue and the realization gate — 48 promotes R-18 … R-22 out of the ledger, fixes the
ledger syncer's `blocked` blindness, runs the CAP-axis namespace pass and lands the Single-Spec
merge; 49 adds a `verified:` line per capability, a doctor effect check, and six effect stories
for CAP-4/-7/-11/-12/-14/-17. No FR added — effect is a definition-of-done discipline over
existing requirements. The ≤400-line living-Dream constraint is retired by operator ruling.
48.1 precedes any ledger write; 47's P-lines precede 44.3. Record:
`sprint-change-proposal-2026-09-09-currency-review.md`.

**2026-09-04 correct-course (foundry cutover — solutioning):** the 40 → 43 + Mason 13 gate
closed 2026-09-03 with nothing downstream of it. The cutover is now under contract as a
sibling Spec, `spec-python-foundry-cutover` (`fnd:CAP-1..7`, extends this chain), with its
own architecture spine (`architecture-python-foundry-cutover-2026-09-04`, `fnd:AD-1..16`)
and steward **Epic 44** (ten stories). **Phase 3 only:** every 44.x is ledger `blocked` while
the operator reviews and refines the solutioning; no FR changes — the cutover is layout,
not product scope, and this PRD's FRs are unaffected. R-17 is Story 44.7; R-23/24/25 fold
into 44.2; R-18..R-22 carry as steward-owned ledger entries (Epic 45 candidate). Record:
`sprint-change-proposal-2026-09-04-foundry-cutover.md`.

## Satellite: bmad-suite lifecycle

> **Folded into this PRD 2026-09-08.** Was `prd-bmad-suite-lifecycle-2026-09-06`, a run-folder named for a CHAIN
> rather than this project — upstream's pattern is `prd-{project_name}-{date}`.
> Its requirements keep their own numbering, qualified `suite:FR-n`, which is how every
> citation now spells them after the 2026-09-08 attribution pass (807 bare FR citations
> read down; 277 resolved by chain-owning path, 352 by epic section and id range).
> **No citation changes meaning.** Renumbering was rejected for the same measured reason
> as the spines: the mechanical attributors top out at 47-80% accuracy.
>
> Original frontmatter — status: final, updated: 2026-09-06.




### 0. Document Purpose

This PRD decomposes `spec-bmad-suite-lifecycle` into functional requirements an epic pass can
group and a `bmad-build` session can implement. **The SPEC is the contract; this document is its
decomposition.** suite:FR-1..suite:FR-10 map 1:1 to CAP-1..CAP-10. Features are grouped by delivery seam —
the same seams the epics use. Mechanisms (provisioning backends, the equivalence-check method,
the `--no-shims` apply, the studio layout, the rehearsal recipe) live in `addendum.md`, so the
architecture pass confirms them rather than reopening them. Station relays are named inside each
FR's acceptance; they are stories in the relayed station's `epics.md`, never extra FRs here.

### 1. Vision

PyForge packages thirteen bmad-suite members and wields a fraction of them. When this PRD is
realized, every member has a verdict and — when wielded — one named station that reaches for it
in daily work; the BMAD-METHOD release cadence is a runbook with owners instead of a heroic
session; and the BMAD estate (`_bmad/`, `.claude/skills/`, `_bmad-output/`, the eight loop homes)
is provably ready for the python-foundry cutover: no shims, no rulebooks, no ungoverned in-place
edits, memlogs that re-render their Specs.

### 2. Target User

**The operator** (rxm7706): decides verdicts, gives outward goes (budget, new repos, upstream
PRs), reads the readiness checklist before opening the foundry.

**The eight station agents** (atlas, doctor, herald, marshal, mason, scribe, steward, warden),
each acting through its persona skill and drained by Marshal: they are the wielders.

#### 2.1 Jobs To Be Done

- Reach for the right suite tool without reading a catalog (routing lives where the persona looks).
- Take a new BMAD-METHOD release through the fleet in one pass, every step owned.
- Know, before the cutover opens, exactly which BMAD-estate prerequisite is still red and who owns it.

#### 2.2 Non-Users

Downstream conda-forge consumers of the suite recipes (Mason's factory flow serves them);
mybmad-dashboard end users (it stays an opt-in local view).

#### 2.3 Key User Journeys

**UJ-1 — Herald ships a release note and a station video.** Herald's persona skill names
`bmad-os-changelog` for the notes and the manticore studio for the video; the studio sits outside
the repo, renders from the deck's speaker notes, and the `.mp4` never enters git.

**UJ-2 — The operator processes bmad-method 6.13.0.** Doctor's drift check warns; the operator
opens `release-cadence.md`, runs the steward pre-flight, applies, proves landed, hands Marshal the
era round, hands Mason the recipe refresh, flips statuses — nothing improvised, every step owned.

**UJ-3 — Warden reviews a PR with two more lenses.** `tea-test-review` and `bmad-os-review-pr`
run as advisory findings beside Warden's gate; the gate's verdict is unchanged by them.

**UJ-4 — Steward checks cutover readiness.** `cutover-readiness.md` reads green on every P line;
`steward upgrade bmad-core` pre-flight lists zero ungoverned local customizations; Story 44.3 is
unblocked on the BMAD side.

### 3. Glossary

- **Suite member** — one of the thirteen active `recipes/bmad-suite/suite-members.yaml` rows.
- **Install class** — how a member reaches the tree: installer-tree, runner-home, own-installer,
  module, cli, plugin-path, scaffold, vscode-extension (`install-class-playbook.md`).
- **Wielder** — the one station whose persona skill routes to a skill (Charter: skills are
  wielded, never worn).
- **Adoption register** — the companion table that governs wiring; a row change is the only way
  wiring changes.
- **Era round** — one round of CAPs on `spec-bmad-611-era-alignment` per BMAD-METHOD release.
- **Readiness P / G lines** — the prerequisites and gaps in `cutover-readiness.md`.

### 4. Features

#### 4.1 Wielding — every member has a verdict, a path and a station

##### suite:FR-1: The adoption register governs wiring *(CAP-1)*
The register holds thirteen rows (verdict, wielder, provisioning path, hazards, status) and is the
only place wiring changes. Acceptance: pipeline-truth's `wired` column agrees with the register
13/13; the channel-product "never wire-everything" constraint and the one-front-door row-6 triage
are superseded/closed by memlog; the register's posture section names both.

##### suite:FR-2: The module wave lands by install class *(CAP-2)*
utility-skills, TEA and bmad-builder are provisioned through `steward provision --module`, and CIS
is re-provisioned. Acceptance: `--list-modules` reports the four installed; the retired-ID guard and
integrity meta-tests stay green; the ten CIS `SKILL.md` carry `--project-root`; a test proves bmb's
`cleanup-legacy.py` is never invoked. Relays: steward 46.2, 46.3, 46.4, 46.8.

##### suite:FR-3: Every adopted skill has one wielding station *(CAP-3)*
The routing table (register § 2) maps each adopted skill to one station; that station's persona
skill and the AGENTS.md managed block cite it; CLAUDE.md carries none of it. Relays: herald 18.2,
doctor 20.4, warden 11.1, scribe 7.1, marshal 31.6, atlas 24.1, steward 46.2/46.4/46.5.

#### 4.2 TEA — the test-architecture module replaces the generator

##### suite:FR-4: TEA is fully adopted *(CAP-4)*
TEA's `bmad-testarch-*` workflows produce every station's `planning-artifacts/test-architecture.md`;
`tea-test-review` runs as a Marshal review lens and a Warden advisory finding; the repo generator
`_bmad/scripts/bmad_tea_playwright.py`, its two marshal meta-tests and its two pixi tasks retire.
Acceptance: 8/8 documents regenerated by TEA with an equivalence check recorded against the
generator's last output; `tea-test-review --base origin/main --min-score N` exits with a real code
on a fixture PR; generator and tests deleted in the same story; Warden's verdict unchanged.
Relays: steward 46.3, marshal 31.1–31.3, warden 11.2.

#### 4.3 Herald's studio and the consented labs skills

##### suite:FR-5: Herald renders through a manticore studio *(CAP-5)*
Manticore is installed in a dedicated studio root outside this repo's `_bmad/`, configured in the
studio's own `_bmad/custom/config.toml`; one station video renders from a deck's speaker notes and
is gitignored. Acceptance: this repo's `_bmad/` is byte-identical before and after; the studio
root is recorded in the register (open question: in-repo gitignored vs `~/pyforge-studio/`).
Relays: steward 46.6, herald 18.1.

##### suite:FR-6: labs-skills arrive by name and by consent *(CAP-6)*
Exactly `mcp-builder` (Atlas), `slides-generator` (Herald), `multi-repo-git-ops` (Marshal) and
`release-please` (Steward) are installed via `npx skills add bmad-labs/skills --skill <name>`.
Acceptance: each has a register row; no other labs skill is present in `.claude/skills/`.
Relays: steward 46.5, atlas 24.1, herald 18.3, marshal 31.6.

#### 4.4 Measurement — the reviewer is measured

##### suite:FR-7: The eval-quality pilot runs *(CAP-7)*
Story 45.2 is unblocked: `eval-quality-smoke`, `eval-quality-review-twin-run` and
`eval-quality-review-replay` exist as pixi tasks; one trial cites `pkg/discount.py:17` on the
mutated arm and not on the clean arm; a per-trial `--max-budget-usd` ceiling applies; none of the
three joins `detectors`. Relays: steward 45.2, mason 14.1 (the `__win` variant).

#### 4.5 Cadence — one runbook per release

##### suite:FR-8: The release cadence is one runbook *(CAP-8)*
`release-cadence.md` orders detect → catalog → pre-flight → apply → prove-landed → era round →
suite refresh → flips → record, with an owner per step; the `@next` prerelease rehearsal is its
optional dry-run. Acceptance: the next release is processed with zero improvised steps; the
rehearsal recipe has run once, report-only, and its findings are in the core-upgrade memlog.
Relays: steward 46.10.

#### 4.6 Cutover readiness — the estate the foundry assumes

##### suite:FR-9: The BMAD estate is provably cutover-ready *(CAP-9)*
`cutover-readiness.md` lists P1–P17 with an owner and G1–G11 with a relay; the gate is every P line
green before Story 44.3. Acceptance: `steward upgrade bmad-core` pre-flight reports zero ungoverned
local customizations; `skf-export` is proven to accept `skills/stations/<x>/`; `_bmad/**` is in
Epic 44's surface; `PROJECTS.md` carries the cutover layout; the foundry Stack has a `bmad-*`
floor row; Epic 44 depends on 14.9 / 30.x; loop-home readiness is defined; the render-HALT and
`frozen-path-changed` detectors exist. Relays: steward 47.1–47.5, marshal 31.4–31.5, doctor
20.2–20.3, and marshal 30.2 (rulebooks).

##### suite:FR-10: The shims are retired *(CAP-10)*
The harness policy names `bmad-build-auto`; the eight loop homes re-render and validate clean;
callers are glossed; the retired-ID guard is widened to the harness file; one `--no-shims` apply
lands `installShims: false` with 21 fewer skill dirs. Acceptance: `bmad-loop validate` 8/8;
`_bmad/_config/manifest.yaml` reads `installShims: false`; the guard stays green. Relays: marshal
30.5 (era-alignment CAP-12), steward 14.9 (core-upgrade CAP-9).

### 4a. Non-Functional Requirements

- **Provision by install class only.** No hand copies into `.claude/skills/`; never
  `cleanup-legacy.py`; never `bmad-module-skill-forge uninstall`.
- **Advisory stays advisory.** TEA and eval-quality outputs never change Warden's gate verdict.
- **Isolation of the studio.** Manticore's upgrade ritual never touches this repo's `_bmad/`.
- **Governed customizations.** Every in-place edit of an installer-owned file is under a spec
  `surface:`; otherwise it lives in `_bmad/custom/**` or is re-applied by core-upgrade CAP-8.
- **History is glossed, not rewritten.** Decks, `docs/specs/`, `pixi.toml` comments keep old names
  with a gloss; live docs and code lead with live names.
- **Ledgers and paths.** Physical-path writes with `BMAD_ACTIVE_PROJECT`; ledgers change only via
  `sprint_plan.py generate` + a scoped `sprint-ledger-sync`.
- **Outward acts need a go.** Upstream PRs, new repos, budget-spending trials.

### 5. Non-Goals (Explicit)

- First-install of bmad-method (the foundry's).
- Refreshing suite conda recipes (Mason's CFE flow).
- mybmad-dashboard into the platform; `bmad-module-template` provisioning; the whole labs marketplace.
- Upstream pull requests.
- The cutover itself (Epic 44).

### 6. MVP Scope

#### 6.1 In Scope (first implementation session — the era tail)
suite:FR-10 (harness flip, callers, `--no-shims` apply) with marshal Epic 30 (30.1–30.5) and steward
14.9; suite:FR-2's CIS re-provision and the skf catalog pin (46.7/46.8); suite:FR-8's rehearsal recipe.

#### 6.2 Out of Scope for MVP (later sessions, drained by Marshal)
suite:FR-2's three module provisions, suite:FR-3 routing, suite:FR-4 TEA, suite:FR-5 studio, suite:FR-6 labs, suite:FR-7 pilot,
suite:FR-9 readiness stories.

### 7. Success Metrics (binary gates)

- `steward suite pipeline-truth`: 13/13 current and `wired` agrees with the register.
- `steward provision --list-modules`: TEA, bmb, utility-skills, CIS installed.
- One station `.mp4` rendered from Herald's studio; this repo's `_bmad/` unchanged.
- The next bmad-method release processed against the runbook with zero improvised steps.
- `cutover-readiness.md` green on every P line; Story 44.3 unblocked on the BMAD side.
- `_bmad/_config/manifest.yaml` reads `installShims: false`; `bmad-loop validate` 8/8.
- Counter-metric: Warden's PR verdict distribution unchanged by the new advisory lenses.

### 8. Open Questions

- Studio root: `presentations/_studio/` (gitignored, in-repo) or `~/pyforge-studio/`? — owner
  herald + steward, decide at Story 46.6.
- `tea-test-review --min-score`: upstream's 80 or calibrate on ten PRs? — owner marshal, 31.3.
- Routing-note home: persona skill AND AGENTS block, or block only (skf-export rewrites AGENTS.md
  at cutover)? — owner steward, 46.1.
- Trial cost accounting for the pilot: steward budget metering or a local `evals/` ledger? —
  owner steward, 45.2.

### 9. Assumptions Index

- TEA's workflows can cover the generator's output; the equivalence check decides, else suite:FR-4
  narrows to the review lens.
- `steward provision --module manticore` cannot target a studio root; the native `--custom-source`
  path is used until a `--studio` flag earns its keep.
- bmad-builder's five skills and skf's sixteen do not collide by name.
- The 2026-09-06 operator decisions are final; the four open questions are not phase-blockers.

## Currency reconciliation — 2026-08-26

Fired by the `spec→prd` staleness edge: the story-spec estate under
`planning-artifacts/specs/` last moved 2026-08-22 (the fleet-wide spec-folder pass making
every spec folder accept a 6.11 `bmad-spec` update, plus the Epic 12/15 extension specs of
the same day), while this PRD's stamp sat at 2026-08-01. Reconciled against the refreshed
brief (same date), the spec estate, and as-built code. Concrete deltas:

**Every FR this PRD carries is shipped.** FR-1..18 as Epics 1–4 (18/18 stories, PRs #157,
#291, #297, #302, #305; whole-build retro `retros/retro-steward-2026-08-08.md`). The
2026-08-08 backlog section's FR-19..21 shipped as Epic 6 (module provisioning), FR-22..26
as Epic 7 (the one-container Guild), FR-27..31 as Epic 8 (Jira ↔ GitHub Projects sync,
extended to 8.1–8.7). `spec-pyforge-steward/SPEC.md` was stamped `status: shipped` in the
2026-08-15 fleet-wide decomposition audit; nothing in the 08-22 spec-folder motion
contradicts an FR here.

**§9's three open questions are closed** — resolved at the architecture step exactly as
this PRD asked: the credential inventory carries a `provenance: issued|observed` field
(OQ1), the host allowlist reads `_http.py`'s existing `resolve_*_urls`/`*_BASE_URL` table
directly (OQ2), and Steward config lives in the repo-root tracked `.steward/` dotdir,
surviving `bmad-switch` (OQ3). See the architecture spine's Consistency Conventions table.

**D6's deploy target was later retired on purpose.** The manual `dashboard-gen` + push
loop this PRD formalized (FR-8..11) was replaced end-to-end and then the generator itself
was deleted: CAP-2 of `spec-pyforge-unifying-strategy` superseded the static Guildhall
console with the CMS-managed Lane 1 front door, and Story 30.2 (2026-08-25) removed
`dashboard-gen` and its inbound references after the console-parity inventory proved
coverage. `steward deploy dashboard` remains as a reconciled diff+commit over
`docs/dashboard/` (Kedro-Viz staging + stub; the build step is a no-op) — FR-9/FR-10/FR-11
semantics intact, FR-8's wrapped task gone with the console. SM-2 was met for the whole
period the manual loop existed.

**Scope boundary, restated for downstream readers.** This PRD decomposes FR-1..31 and is
the durable record of them. Everything the station shipped past FR-31 — Epics 9–38:
secure live dashboards, the python-agent-platform host, the Canopy chain (18–30),
install-class wiring, CAP-18 plugins, skill/persona, the query plane (34), Lane 3, the
five-tier roster drain (37.1, 2026-08-26), and the factory stdio MCP translator (38.1,
retroactive, 2026-08-29) — decomposes from its own owned specs
(`spec-secure-live-dashboards`, `spec-python-agent-platform`,
`spec-pyforge-unifying-strategy` with `prd-pyforge-unifying-strategy-2026-08-24`,
`spec-mcp-factory-stdio-translator`, and siblings), per this PRD's own 2026-08-08 rule: a
capability decomposes here iff its Dream is `owner: steward` **and** no later chain owns
it. As of 2026-08-26 the station ledger reads 37/37 epics, 131/131 stories `done`.

**Fact updates in place this pass:** the §3 pixi-estate count (~14 → 27, annotated), and
the FR-27..31 preamble's "greenfield / nothing exists today" claim (now dated and closed
by Epic 8). No FR text was altered.

## Currency reconciliation — 2026-08-29

Fired by the same `spec→prd` staleness edge, a second time: `spec-pyforge-steward`'s
`.memlog.md` moved to 2026-08-29 while this PRD's stamp sat at 2026-08-26. Two separate
motions moved it, both checked against this PRD's FR-1..31 and its `owner: steward`
decomposition rule above — neither adds or changes an FR here:

**Spec-surface drift reconciliation (marshal Epic 13's ongoing maintenance practice).**
16 files governed by `spec-pyforge-steward`'s blanket glob had drifted since the last
baseline stamp. Each was traced individually (not bulk-stamped) to a contract that
already exists elsewhere: the fresh-clone/provision/CLI cluster to
`spec-bmad-suite-install-class-wiring`; the suite-report cluster to Story 15.1's own spec;
the five-tier cluster to Stories 29.3/37.1's own specs; the deploy-profile-plugins cluster
to Story 32.2's own spec (real, tracked growth beyond this PRD's original FR-8..11
Pages-dashboard-only scope, but the contract for it already lives in that dedicated
spec, not here); the remaining two files (portal-slice provision list, SKF skill/persona)
to Stories 33.1/33.2's own specs; and two files (the library catalog, a pyproject.toml pin)
to routine dependency upkeep this PRD's own surface note already anticipates. Zero new
capability against FR-1..31 or against the `owner: steward` boundary rule.

**Epic 38 — retroactive decomposition of an already-shipped spec.** `spec-mcp-factory-
stdio-translator` (Dream `owner: steward`, via `mcp-era-isolation.md`) shipped its CAP-1/
CAP-2 translator on 2026-08-26 — the same day the operator authorized it, once slice 1
(`#858`) landed — but no epic ever cited it, so `chain-completeness` flagged the Spec as
undecomposed for three days. Filed as Epic 38/Story 38.1 on 2026-08-29, paperwork only, no
new code. Per the scope-boundary rule restated above, this capability decomposes from its
own owned spec, not from this PRD's FR list — Epic 38 is named in the restated boundary
paragraph for the same completeness reason Epic 37 was.

**No FR text altered.** As of 2026-08-29 the station ledger reads 38/38 epics, 132/132
stories `done`.

## Currency reconciliation — 2026-09-05

Fired by the `spec→prd` staleness edge a third time: `spec-pyforge-steward`'s `.memlog.md`
moved to 2026-09-05 (twice) while this PRD's stamp sat at 2026-09-02. Both motions, plus one
new Spec, checked against FR-1..31 and the `owner: steward` decomposition rule above —
nothing adds or changes an FR here:

**Post-merge follow-up-review landing (PR #1056).** bmad-loop's follow-up-review pass had
committed into the dispatch worktrees of Stories 41.3, 41.4, 42.1, 42.2 and 43.2 *after* each
story PR merged, so five review-driven tightenings (governance gates, broker TLS
verification, MCP transport auth, rate limits / run bounds, station API contract) and 21
`deferred:` findings never reached `main`. Landed as one batched PR with a lint / mypy /
deferred-work / spec-surface reconcile commit. Code-level hardening of already-decomposed,
already-`done` stories — zero new capability against FR-1..31.

**bmad-suite 2026.9.5 refresh (Story 45.1).** `suite.py`'s roster swapped
`bmad-method-wds-expansion` (upstream `deprecated: true`, folded into BMM as `bmad-ux`) for
`bmad-eval-quality`, seated under a new install class `cli` (a bare CLI with nothing to wire
into `_bmad`; PATH-presence predicate). The install-class taxonomy is
`spec-bmad-suite-install-class-wiring`'s contract and the metapackage roster is
`spec-bmad-suite-metapackage`'s; this PRD's FR list is untouched.

**Epic 45 — a new Spec decomposed the day it was written.** `spec-bmad-eval-quality`
(Dream `docs/dreams/bmad-eval-quality.md`, `owner: steward`; CAP-1 suite membership, CAP-2
the review-catches-a-planted-defect pilot) became Epic 45 / Stories 45.1 (in-progress —
recipe built and tested green locally, channel upload + pixi pin pending) and 45.2 (blocked
on the twin-run pilot). Per the boundary rule it decomposes from its own owned Spec, not
from this FR list — named here for completeness exactly as Epics 37 and 38 were.

**No FR text altered.** As of 2026-09-05 the station ledger reads 45 epics; 170 stories — 153 done, 15 blocked, 1 backlog, 1 in-progress.

## Currency reconciliation — 2026-09-08

Fired by the `spec→prd` staleness edge a fourth time: `spec-pyforge-steward`'s `.memlog.md`
moved to 2026-09-08 while this PRD's stamp sat at 2026-09-05. The motion, and the sibling
epics edit that landed with it, checked against FR-1..31 — neither adds nor changes an FR here:

**`_persona_mentions` precision + scan breadth (`tests/meta/test_adoption_register.py`).** One
shared test helper was indicted independently by two projects' deferred-work ledgers that never
referenced each other — `steward/DW-FU-46-1-2` (scans only `SKILL.md` and `customize.toml`) and
`atlas/DW-FU-24-1` (bare substring match, never the routing line's constraint text). The helper
now anchors both ends of the match on a non-word boundary, so `bmad-spec` no longer matches
inside `bmad-spec-foo`, and reads `README.md` plus every `reference/*.md` the persona skill
carries. This tightens how an existing, already-decomposed obligation is *verified*; it states no
new obligation. `atlas/DW-FU-24-1` deliberately stays open, since its own claim — that the check
never asserts the routing line's stated grammar-constraint text — remains true.

**Story 43.7 (`epics.md`).** `mason/DW-13-2-2` deferred the dbgpt-sidecar Celery REST round-trip
and SQLite metadata-store validation on Python 3.14 to Story 43.6, which then closed `done`
without doing it — 43.6's acceptance criteria are the pin flip, the re-lock, the regenerated
`environment.yaml` and an import smoke, none of which exercise Celery or the metadata store. The
work was unowned rather than late, so Story 43.7 was authored to own it. It decomposes the
existing `pap:CAP-5` / `pap:CAP-6` platform-image capabilities; no FR here changes. The blocker
the ledger recorded is also stale — `pixi list -e dbgpt-sidecar` now resolves `python 3.14.7`,
`dbgpt-app 0.8.2`, `dbgpt-ext-rag 0.8.2` and `onnxruntime 1.28.0 py314h112547c_0_cpu`, so the
`onnxruntime <=1.18.1` cp314 gap that caused the deferral is closed.

**No FR text altered.**

## Currency reconciliation — 2026-09-09

`spec→prd` edge for `spec-pyforge-unifying-strategy` (`updated: 2026-09-09`, hand-edited past its
memlog per the standing exception). Motions: `:488` amended (operator ruling — the living Dream's
line count is not a constraint), `:73`/`:315` floor `3.12.*` → `3.14.*` (43.6 shipped 2026-09-03),
Constraints block *Correct-course 2026-09-09* (syncer sticky `blocked`; `verified:` line per CAP;
qualified CAP citations), § Residual (2026-09-09), `open_questions` `realization-gate-home` /
`single-spec-merge-timing`, two research companions. **FR delta: none.** Epics 48–49 (sixteen
stories) decompose the Residual and the new Constraints; § 14 carries the dated paragraph. Record:
`sprint-change-proposal-2026-09-09-currency-review.md`.

## Currency reconciliation — 2026-09-14

`spec→prd` edge, this time for **this station's own kernel Spec** rather than the Unifying
Strategy: `spec-pyforge-steward`'s SPEC.md moved to 2026-09-12 and its memlog to
2026-09-13T23:59 while this PRD sat at 2026-09-08.

**What moved, and why the FR delta is none.**

1. **Dated `verified:` lines on CAP-1..CAP-4 (2026-09-11 sweep).** All four hold, and they
   hold against *live* evidence rather than test counts alone: `steward keys list --json`
   returns real inventory entries with a `provenance` field and `secrets: []` (no raw value
   printed); `steward deploy status` returns a real commit SHA and timestamp read from git
   history with no separate state store; `steward provision --list --json` enumerates the
   real `pixi.toml` environments and `--env not-a-real-env` produces a clear error listing
   the valid names rather than pixi's raw one; `steward budget show --json` returns `[]`
   cleanly with none declared, and a repo-wide grep for `kubecost`/`opencost`/`infracost`/
   `boto3`/`google-cloud-billing` under the package returns zero hits. **One is scoped
   honestly and that scoping is worth preserving:** CAP-3's `--runner bmad-loop`
   materialization was *not* re-exercised live (it creates a real worktree) and the Spec
   says so in the same breath, leaning on `test_provision_runner.py` instead. A verification
   that states what it did not do is the only kind worth trusting.
2. **A 4-path `surface-drift-exclude:` block.** `dashboard/asgi.py`,
   `dashboard/consumers.py`, `dashboard/routing.py` and `upgrade.py` — all also governed by
   `pyforge-marshal/spec-pyforge-core`, which reconciles them on its own cadence. Coverage
   is unchanged; only this kernel's own drift tracking for those four is off. Detector
   bookkeeping, no FR.
3. **A bulk post-outage surface reconcile of five already-landed stories (2026-09-14).**
   The cutover flag reader + replay harness, per-run `track.json` assembly, Hub Guard
   library exposure, the foundry strangler kit, and the suite-skip work all drifted this
   Spec's baseline **while a ~5-day GitHub Actions billing outage kept `spec-surface` CI
   from ever running**. The reconcile is bookkeeping; the *lesson* is not, and it belongs at
   PRD altitude because it is about how this station knows things: a detector that cannot
   run does not report "unknown", it reports nothing, and five days of drift arrived at once
   the moment CI resumed. That is the same fail-open shape this station already guards
   against in `steward keys` (a credential check that cannot reach its source must not read
   as clean).
4. **Story 53.6 re-keyed the in-repo Frame preflight from `name` onto `identifier`.**
   Verified live: `frames.py` now carries `COMPANY_IDENTIFIER`/`PUBLISHER`, lists
   `identifier` in `REQUIRED_FIELDS`, and indexes by identifier. Frame Spec v0.3 §4.2.1
   makes `identifier` the one mandatory identity element and §5.3 SHOULDs a `qualified-ref`;
   the element profile marks `title` — which the Markdown `name` key aliases — as MUST NOT
   be slug-constrained. Keying preflight off `name` was therefore keying identity off a
   *label*, and off a string that was simultaneously the Frame key and the Python
   distribution name. The full record lives in `spec-intelligence-hub`'s memlog (CAP-2);
   this PRD's FR set is untouched because the Intelligence-Hub adoption is decomposed there,
   not here.

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a
regex): **244 story keys — 231 `done`, 10 `blocked`, 3 `backlog` — across 58 epics** (56
`done`, 2 `in-progress`).

**One repair made in passing, and it is not cosmetic.** This PRD's frontmatter
`currency_review:` value was **invalid YAML at HEAD** — an unquoted scalar containing
`: ` sequences, so `yaml.safe_load` failed on the whole block. It parsed only because
`fleet_scan._frontmatter_scalars` is a deliberately naive line reader. The value is now a
properly quoted scalar with its inner quotes escaped. No text was removed. Recorded because
the failure mode is silent in exactly the tooling that reads it most.

**No FR text altered.**

## Currency reconciliation — 2026-09-17

`spec→prd` edge after the one-chain-per-station steward fold. `spec-pyforge-steward`
re-derived on 2026-09-17 as CAP-1..145 covering 35 Dreams and 31 absorbed pointer Specs,
while this PRD's `updated:` stayed at 2026-09-14 even though `fr-derivation-from` already
read `2026-09-17`.

**What moved, and why the FR delta is none.**

1. **Station Spec remint, not a new FR set.** Absorbed capabilities were already
   decomposed as Epics 9–64 on their own Specs. The remint writes provenance
   (`← spec-<old> CAP-m (shipped <date>)`) onto sequential CAP-1..145. Kernel
   FR-1..18 (keys, deploy, provision, budget) are the same four duties this PRD
   has always bound.
2. **Station contract stays `ready` / Dream `specified`.** Per the marshal CAP-8
   pilot and CHAIN-STANDARD, the station Spec is not flipped to `shipped` by a
   fold, and the station Dream is not flipped to `realized`.
3. **Pointer SPECs keep companions; bodies are record.** That is CHAIN-STANDARD
   §7 item 3. No requirement here changes because a pointer folder still holds
   its spine or inventory files.
4. **Smashed Dream frontmatter was a parse defect, not a product change.** The
   fold concatenated `---` onto `title:` / `status:`, so `_frontmatter_scalars`
   could not read `owner: steward` and the chain-currency coherence checkpoint
   marked the station `unowned`. Restored parseable frontmatter. Owner, type,
   and status values are unchanged.

**No FR text altered.**

## Currency reconciliation — 2026-09-20

`spec→prd` edge: `spec-pyforge-steward`'s `.memlog.md` moved to 2026-09-20T02:28 while this PRD
sat at 2026-09-17 — three days, past the runbook's 2-day grace.

**What moved, and why the FR delta is none.** Six entries, all landing bookkeeping on capabilities
this PRD already covers through the 2026-09-17 fold: Story 61.1 (corridor transports, PR #1528),
61.2 (work passport + core schema, PR #1532), 61.3 (as-of glass and mailed query, PR #1539) — each
an autonomous dispatch landing whose entry names the paths the session left unreconciled; the
`DW-FU-61-2` closure (a PR-label deferral resolved at landing); and two co-governor reconciles for
doctor Story 30.1's station README pointer line. Epic 61 decomposes `spec-work-passports-dated-
extracts` (absorbed as CAP-141..145); nothing here is a new requirement of Steward. `updated:` bumped
to record that the check ran.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this PRD. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-24

`spec→prd` edge: `spec-pyforge-steward`'s `.memlog.md` moved to 2026-09-24T20:08 while this PRD
sat at 2026-09-20 — four days, past the runbook's 2-day grace.

**What moved, and why the FR delta is none.** Two entries: the Story 63.4 (`steward session
check`) surface-reconcile naming `src/shared/packages/pyforge-steward/src/pyforge/steward/session.py`
and its four entry-point wirings (`cli.py`, `.claude/hooks/session-start.sh`,
`.cursor/environment.json`, `.github/workflows/copilot-setup-steps.yml`, plus
`pyforge-marshal`'s `dispatch.py`), and a merge-reconcile entry unioning that motion against a
concurrent co-governor edit from marshal Story 46.2 on the shared `spec-pyforge-core` memlog
(`context_bundle.py`) landed via PR #1588 while this branch was in flight. Story 63.4 decomposes
Epic 63 (`environment pyforge-guild`, spec-pyforge-steward CAP-5) — consolidating seven
pre-existing, independently-checked session-precondition findings (Tier-3 feed absence, stale
`BMAD_ACTIVE_PROJECT`, symlink/marker desync, and others already described piecemeal across
existing duties) into one verdict duty run from every session entry point. CAP-5's own scope
(the `pyforge-guild` environment is the default for every agent and harness) already covers
verifying that a session's environment preconditions hold; this story adds a duty, not a
requirement. `updated:` bumped to record that the check ran.
