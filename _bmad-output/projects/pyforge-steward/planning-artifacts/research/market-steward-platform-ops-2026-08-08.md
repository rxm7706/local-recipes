---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/domain-steward-platform-ops-tooling-research-2026-07-25.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/retros/retro-steward-2026-08-08.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/budget.py
  - docs/dreams/unified-container.md
workflowType: 'research'
lastStep: 6
research_type: 'market'
research_topic: 'Steward — post-ship competitive/analogue landscape: Vault-class credential lifecycle, Terraform/Pulumi-class provisioning, Kubernetes quota-class resource ceilings, GitHub Actions runner provisioning'
research_goals: 'Now that all 18 stories / 4 epics are shipped, compare what Steward ACTUALLY built (not what it planned) against the four nearest external analogues, per verb — keys vs Vault/Vault Agent/OpenBao, provision vs Terraform/Pulumi/OpenTofu, budget vs Kubernetes ResourceQuota/LimitRange, runner provisioning vs GitHub Actions self-hosted/ARC — to locate real gaps worth closing, properties Steward already matches, and market patterns Steward must continue to refuse.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
mode: 'headless-express'
---

# Research Report: Steward — Market/Analogue Landscape (Post-Ship, 2026-08-08)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Market research (headless/express — one of 8 parallel PyForge station research refreshes). This is the first `market-*` file for pyforge-steward; the 2026-07-25 domain report treated the comparable-tool landscape pre-ship. This report is different in kind: Steward is now **fully shipped (18/18 stories, PRs #157, #291, #297, #302, #305)**, so every comparison below is against real merged code in `src/shared/packages/pyforge-steward/src/pyforge/steward/`, not against a planned design.

---

## Framing: what "market" means for a shipped internal station

Per the domain report's A1, Steward has no literal market competitors — it is an internal
station, not a product. "Market research" here means: **for each shipped verb, name the
external tool an operator would reach for if Steward didn't exist, compare the shipped
mechanics point-by-point, and extract (a) properties Steward already matches at 1/1000th the
operational weight, (b) real gaps the analogue exposes, (c) patterns to keep refusing.** The
comparisons are chosen per the operator's explicit direction: HashiCorp Vault / Vault Agent
(keys), Terraform / Pulumi (provision), Kubernetes ResourceQuota / LimitRange (budget), and
GitHub Actions self-hosted runner provisioning (the `--runner` half of provision).

---

## 1. `steward keys` vs. HashiCorp Vault / Vault Agent / OpenBao

### What Steward actually shipped (Epic 1, Stories 1.1–1.7)

- **Host-scoped credential resolution** (`HostScopedCredential` + `_canonical_host` +
  `resolve_headers`, `keys.py:109-225`) — an allowlist gate deciding *whether* ambient auth
  may attach to a URL, delegating header-building to `_http.py`'s `auth_headers_for` (FR-1,
  FR-7: the JFrog cross-host leak closed as a named regression).
- **At-rest encryption** as thin `age`/`age-keygen` subprocess wraps (FR-2) — no vendored
  crypto, `-` stdin sentinel rejected, closed stdin for unattended runs.
- **Rotation** (`rotate_identity`, FR-3): generate fresh identity → re-encrypt every secret
  the active scope owns via a private tempdir → retire the old entry, append a new
  generation-named entry. Serialized by `fcntl.flock` + atomic `os.replace` after a close-out
  review found the concurrent rotate/revoke lost-update race — proven with two real racing
  threads.
- **Inventory** (`.steward/keys-inventory.yaml`, FR-5): name/scope/provenance/status/
  last_rotated + a filesystem *pointer* to the identity — never key material. `yaml.safe_*`
  only.
- **Audit** (FR-4): a deliberately single-shape AST drift scan (the pre-fix
  unconditional-injection pattern) + a 3-pattern plaintext-secret scan (sk-ant, age identity,
  PEM header) with fail-loud semantics (unreadable subtree, dangling symlink, UTF-16 NUL
  interleave all raise or are caught — three review passes hardened this).
- **Revocation** (FR-6): a pure local record write plus provenance-appropriate manual
  remediation text; **no provider API client anywhere**, pinned by an AST invariant test.

### Vault comparison, point by point

| Property | Vault / Vault Agent | Steward shipped | Verdict |
|---|---|---|---|
| Standing service | Raft HA cluster, unseal ceremony, HCL policy engine | None — CLI + encrypted files in Git (NFR-1) | Refusal held; correct at this scale |
| Rotation without breaking trusted readers | KV-v2 versioning / transit keyring versions: old version stays readable until explicitly destroyed | `scope` stable + `name` per-generation: retired record and replacement coexist inspectably; secrets re-encrypted in place | **Property achieved** — see § domain re-validation in the refreshed domain report |
| Secret delivery to consumers | Vault Agent auto-auth + template sinks (render secrets to files, restart consumers) | `steward keys decrypt --output <path>` — manual, per-invocation | Gap, but a *deliberate* one: no daemon (AD-4-class refusal). Vault Agent's sink model is the pattern to borrow **if** unified-container ever needs in-container secret materialization at boot |
| Leases / TTLs / dynamic secrets | Core feature; credentials expire by construction | None — rotation is on-demand only (FR-3), pinned by `test_no_rotation_scheduler_exists` | Aligned with NIST 800-63B Rev 4 risk-triggered posture (domain report § 4); TTLs remain the one Vault property with no Steward analogue at all |
| Revocation reach | Calls the provider (database, cloud IAM) to actually kill the credential | Record-only + printed remediation (`_remediation_for`, incl. the JFrog-specific line "this tool cannot call JFrog's revocation API") | Honest gap, honestly labeled — the same "honest stub" doctrine as `budget check` |
| Audit trail | Full request audit log device | Inventory file history in Git + `keys audit` scans | Adequate: Git *is* the audit log for a repo-centric tool |
| Host scoping of a credential | Policies bind tokens to paths, not egress hosts — Vault does not actually solve the JFrog-leak shape; egress scoping is out of its model | `HostScopedCredential` gates attachment by destination host | **Steward is ahead of the analogue here.** The `_canonical_host` three-pass convergence (empty hosts → IPv6 `rsplit` corruption → `https:host` colon-parsing) is the cost of owning a property Vault doesn't offer |
| License / fork risk | BUSL-1.1 since 2023; OpenBao (MPL-2.0, LF) is the OSI path | `age` is Apache/BSD-class, stable | No exposure |

### Takeaways

1. **The one Vault property genuinely worth watching is Vault Agent's sink/template model** —
   not for bare-metal Steward, but as the shape of "secrets appear inside the unified
   container at boot" (see the technical addendum's container feasibility section). A
   `steward keys materialize --scope <s> --into <dir>` verb would be the no-daemon analogue.
2. **TTL/lease semantics are the largest conceptual gap** but have no forcing incident yet;
   defer until a credential with a real expiry (OIDC-federated token) enters the inventory.
3. The retro's lesson 3 (security-critical string normalization deserves its own story-sized
   surface) is the market-comparison's cost side: Steward bought a host-scoping property the
   incumbent doesn't have, and paid three review passes for one normalization function.

---

## 2. `steward provision` vs. Terraform / Pulumi / OpenTofu

### What Steward actually shipped (Epic 3, Stories 3.1–3.4)

Four flags, all thin wraps (AD-1/AD-5): `--env` (`pixi install -e <name>` after validating
against `pixi.toml`'s `[environments]` table), `--runner bmad-loop --env <name>`
(`scripts/bmad-loop-worktree` + `pixi install` inside the fresh worktree, with the
partial-state review fix: a worktree that exists when the env install fails is *named* in the
error, never silently orphaned), `--list [--json]`, and `--verify` (wrapping the **exact**
`.github/workflows/scripts/linter.py:65-70` comparison semantics rather than re-deriving
them — AD-1 under real pressure, per the retro).

### Comparison

| Property | Terraform / Pulumi / OpenTofu | Steward shipped | Verdict |
|---|---|---|---|
| Desired-state declaration | HCL / general-purpose language programs | `pixi.toml [environments]` — Steward never writes it, only reads (19 envs today, verified via `tomllib` this pass) | Steward is stateless-by-delegation: the manifest is someone else's contract |
| State file | The defining artifact (tfstate; Pulumi state backend) — and the defining failure mode (drift, corruption, locking) | **None.** `pixi.lock` + the filesystem are the state; `pixi install` is idempotent convergence | Strong position: Steward gets convergence without owning a state file. Do not add one |
| Plan/apply split | `terraform plan` before `apply` | `--list`/`--verify` are the read side; `--env` applies directly with no diff preview | Minor real gap: no "what would materialize" preview. Low value while `pixi install` is cheap and idempotent; revisit only if provisioning grows destructive operations |
| Drift detection | `plan` against live infra | `--verify` (environment.yaml ↔ pixi.toml sync gate) | Equivalent-in-kind for the one drift surface that has ever actually bitten this repo (the ungated PR CI env-sync gate) |
| Ephemerality | OpenTofu ephemeral resources / write-only attributes | Worktrees are naturally ephemeral (torn down after runs); envs are cached | Philosophically aligned already |
| Providers/plugins | 3,900+ providers | Exactly two backends: `pixi`, `bmad-loop-worktree` | Correct restraint; the third backend is already dreamt: `--module` (bmad-module-provisioning Dream, 2026-08-07) — the first genuine post-ship growth vector for this verb |

### Takeaways

1. **The bmad-module-provisioning Dream is the Terraform-shaped growth path done right**: add
   a backend (npm-distributed BMAD module installers, driven headlessly), not a state file.
   Epic 3's `--runner` story is its named structural precedent in the Dream itself.
2. The `_run_runner` partial-state error reporting ("worktree X provisioned, but pixi install
   exited N") is Steward's small-scale answer to Terraform's tainted-resource problem —
   worth keeping as the template for any `--module` failure path.

---

## 3. `steward budget` vs. Kubernetes ResourceQuota / LimitRange

### What Steward actually shipped (Epic 4, Stories 4.1–4.3)

`.steward/budget.yaml` with `set --cap <amount><currency>/<period>` (validated **before** any
file write, so a malformed cap can never corrupt the file), `show [--json]`, and `check` —
which **always** reports "no metered spend source configured" via a dedicated
`EXIT_BUDGET_NOT_CONFIGURED` exit code. The honest-stub property is *structural*: an AST
invariant test (`test_no_cost_integration_sdk_imported_in_budget`) proves no cost SDK is
imported, not just that none is called. Close-out review found and fixed an uncaught
`TypeError` on a malformed `ceilings` field and a silently-unvalidated `declared_at`.

### Comparison

The Kubernetes quota model decomposes into exactly the three parts Steward's verb makes
explicit:

| Part | Kubernetes | Steward shipped |
|---|---|---|
| Declaration | `ResourceQuota` / `LimitRange` objects (machine-readable, namespaced) | `budget.yaml` ceilings — FR-16, machine-readable, tracked in Git |
| Display | `kubectl describe quota` (used/hard columns) | `budget show` — but with no "used" column, because... |
| **Enforcement point** | **The admission controller** — a request exceeding quota is *rejected at submission time* | **None, and it says so.** `budget check` exits `EXIT_BUDGET_NOT_CONFIGURED` rather than fabricating a pass/fail |

**The market lesson is precisely the one K8s teaches: a quota without an admission point is
documentation.** Kubernetes quota only works because every resource request funnels through
one API server that can say no. Steward's estate has no such funnel today — spend happens in
GitHub Actions minutes, Anthropic API tokens (bmad-loop stories), and operator time, none of
which pass through a Steward-controlled chokepoint. Epic 4's conservatism (PRD D1: no
Kubecost/OpenCost/Infracost integration) was therefore correct — but the analogue names the
two conditions under which `check` should graduate from honest stub to real gate:

1. **A meter appears**: the GitHub Actions billing API (minutes used) and the Anthropic
   usage/cost surface are the two real candidate spend sources; either one turns `check`
   into "used vs. hard" with a genuine exit code. This is the cheapest possible upgrade and
   needs no K8s-class machinery.
2. **A funnel appears**: if the unified-container Dream lands, the container boundary itself
   becomes the first real admission point Steward has ever had — a place where "may this run
   start, given the ceiling?" can actually be asked (LimitRange's per-pod defaulting maps
   onto per-loop-run token/minute caps, which auto-memory notes bmad-loop's
   `max_tokens_per_story` currently does *not* enforce). That is the first credible
   enforcement story for FR-18's successor.

---

## 4. `steward provision --runner` vs. GitHub Actions self-hosted runner provisioning (ARC)

### The analogue

GitHub's ecosystem answer to "provision an execution environment per job" is the
actions-runner-controller (ARC) pattern: **ephemeral, single-job runners** (registered with
short-lived JIT tokens, deregistered on completion), scaled as container pods, with the
security doctrine "never reuse a runner across trust boundaries." The older static
self-hosted runner (long-lived VM, manually registered PAT) is the pattern the industry has
spent five years migrating away from.

### Steward's shipped local analogue

`steward provision --runner bmad-loop --env <name>` is structurally the ARC pattern at
single-machine scale: one command materializes an isolated execution home (git worktree via
`scripts/bmad-loop-worktree`) plus its environment (`pixi install` inside it), name-keyed by
the convention that every `pyforge-*` pixi env is named identically to its BMAD project slug
(Story 3.2's Design Notes — the reason there is no separate `--slug` flag).

| Property | ARC ephemeral runners | Steward shipped |
|---|---|---|
| Isolation unit | Container pod per job | Git worktree per loop run |
| Registration credential | JIT token, expires | None needed (local trust domain) |
| Teardown | Automatic on job completion | Owned by bmad-loop/worktree scripts, not Steward — Steward provisions, never reaps |
| Known sharp edge | Pod spec drift | **Worktree path length**: root >~173 bytes panics pixi-build-python (auto-memory, `project_bmad_loop_worktree_path_length_limit`) — a constraint ARC never has and any containerized runner path must respect |

### Takeaways

1. **The gap worth naming: Steward provisions but does not reap.** ARC owns the full runner
   lifecycle; Steward's verb is create-only (list/verify are read-only). A `--reap` or
   status surface for stale worktrees is the smallest lifecycle-completion step, and the
   `feedback_worktree_remove_deregisters_on_failure` memory entry (failed `git worktree
   remove` still de-registers; orphaned dirs need `chmod -R u+w`) documents exactly the
   failure mode a reaping verb would own.
2. **ARC is the direct bridge to the unified-container Dream**: ARC's whole point is runners
   *as containers*. If PyForge ships as one image, "provision a runner" becomes "start a
   container from the image with a worktree volume" — Steward's `--runner` flag is the
   natural CLI face for that, and this is the provisioning half Marshal's parallel research
   does not cover (per the operator's split).

---

## 5. Cross-cutting verdicts

1. **Every refusal the pre-ship domain research recommended was actually honored in code**,
   and four of them are now *pinned by invariant tests* rather than prose: no rotation
   scheduler, no provider revocation client, no cost SDK import, no secret value in `list`
   output. This is a stronger market position than most internal tools ever reach — the
   non-goals are machine-enforced.
2. **Steward exceeds its analogues on exactly one axis** (host-scoped egress gating of
   credentials, § 1) and honestly stubs exactly one (budget enforcement, § 3). Both facts
   should be stated in any future PRD rather than rediscovered.
3. **The three growth vectors this landscape supports, in priority order**: (a) `provision
   --module` (bmad-module-provisioning Dream — analogue-backed by Terraform's
   backend-not-state-file lesson, already steward-owned), (b) a real spend meter behind
   `budget check` (GH Actions billing API first), (c) runner lifecycle completion (reap) and
   the container-runner convergence with the unified-container Dream.
4. **What to keep refusing**: standing services (Vault, ArgoCD-class), a state file
   (Terraform's defining liability), a scheduler, and any provider SDK — each refusal is
   currently cheap because an invariant test or an architecture decision (AD-1/AD-4/AD-5)
   already guards it.

---

## Source notes

Repo-internal, read directly this pass: `keys.py`/`provision.py`/`budget.py`/`deploy.py`
(shipped code), `retro-steward-2026-08-08.md`, `epics.md` (FR-1..FR-18, NFR-1..NFR-7),
`docs/dreams/unified-container.md`, `docs/dreams/bmad-module-provisioning.md`,
`docs/dreams/enterprise-airgap.md`, repo-root `pixi.toml` `[environments]`, auto-memory
entries (`project_bmad_loop_worktree_path_length_limit`, `feedback_bmad_loop_blind_spots`,
`feedback_worktree_remove_deregisters_on_failure`). External-tool characterizations (Vault/
Vault Agent/OpenBao, Terraform/Pulumi/OpenTofu, Kubernetes ResourceQuota/LimitRange/
admission control, GitHub ARC/ephemeral runners) are carried from the 2026-07-25 domain
report's verified sources plus established knowledge; no fresh web pass was run (offline
refresh). Confidence: high for all Steward-side claims (direct code read); medium for
external-tool feature details not re-verified since 2026-07-25 — none is load-bearing beyond
the pattern level.

## open_questions[]

- **OQ1**: Should `budget check`'s first real meter be the GitHub Actions billing API or the
  Anthropic usage surface? Both are env-var-authenticated HTTP reads that fit the `_http.py`
  routing chain; pick whichever the operator actually watches.
- **OQ2**: When `provision --module` (bmad-module-provisioning) reaches Spec, does module
  state ("installed vs. available") live in a new `.steward/` file (inventory precedent) or
  derive from the filesystem (`derive-don't-declare` memory rule)? The keys-inventory
  precedent argues for a file; the memory rule argues for derivation. Resolve at Spec time.
- **OQ3**: Does runner *reaping* belong to Steward (lifecycle symmetry with ARC) or stay with
  Marshal/bmad-loop's own teardown? The provision-not-reap split is currently implicit;
  either answer is fine, but it should be written down (see the domain refresh's
  cross-station section).
