---
title: Product Brief — Steward
status: draft
created: 2026-07-25
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: currency reconciliation — research->brief: the 2026-09-25 BMAD-method whitepaper verification landed in research/; no change to Steward's charter. Prior 2026-09-14
---

# Product Brief: Steward (`pyforge-steward`)

## Executive Summary

Steward is the platform, deployment, and operations station of the pyforge ecosystem — a real, installable Python package (dist `pyforge-steward`, module `pyforge.steward`, CLI `steward`) that owns the four duties an ownership audit found orphaned on 2026-07-23: **provisioning** the engines the factory runs on (pixi environments, bmad-loop runners, CI images), **deploying** the services the factory ships (the Pages dashboard, `presenton-pixi-image` on OpenShift, air-gap bundle installs), **holding the keys** (credential issuance, scoping, rotation, revocation), and **enforcing budgets** (machine-readable resource ceilings). It exists because two of these duties already failed silently in this repo — a leaking JFrog API key and a committed Anthropic API key that needed history rewritten to remove — and nothing in the pyforge Crew currently owns "no privilege outlives its deployment" as a first-class responsibility. Steward is not a new platform to operate; domain and technical research (2026-07-25) both converge on the same verdict: it is a thin CLI that formalizes what this repo's maintainer already does by hand, wrapping already-proven local tools (`_http.py`'s routing chokepoint, `gh`, pixi, and this repo's own `pyforge-warden` packaging pattern) rather than reimplementing Vault, Backstage, or Kubecost at a scale this one-person factory doesn't have.

## The Problem

This repo has already paid for the absence of a credential-lifecycle owner, twice. `.claude/skills/conda-forge-expert/scripts/_http.py` attached the `JFROG_API_KEY` auth header to *every* outbound request — including calls to `pypi.org`, `github.com`, and AWS S3 — regardless of destination host, for as long as the variable stayed exported in a shell (documented in `docs/reference/enterprise-deployment.md` § "Cross-host credential leak"). Doctor-class observation and a human caught it; a code-level `skip_auth` guard now exists, but nothing systematically prevents the next credential from being issued the same way. On 2026-07-24, a `sk-ant` API key and a document referencing it were committed to git, requiring history to be purged and the key rotated — a second, independent instance of the same underlying gap: privilege that outlived its intended scope, caught after the fact rather than prevented. Beyond credentials, three more duties are done by hand today with no formal owner: the Pages dashboard is built and pushed manually (`dashboard-gen` + `git push`, no reconciliation loop); the 14-environment pixi estate and its `environment.yaml` sync discipline exist but have no provisioning CLI; and the "$1500/month locked" budget doctrine the Dream names has no enforcement mechanism at all — it is a stated intention, not a checked one.

## The Solution

`steward` is a CLI with four subcommand groups mirroring the four duties, structured as independent, pluggable engine modules (mirroring the `interfaces.py` + null-engine pattern already proven in the sibling `pyforge-warden` package) so each duty ships, tests, and evolves on its own timeline. Concretely: `steward keys` wraps `_http.py`'s existing host-scoped/`skip_auth` routing and extends it to Git-native at-rest secret handling (`age`/SOPS-class encryption, no standing secrets-manager service) with rotation modeled on 2026 best practice (risk/compromise-triggered, not blind-calendar, per NIST SP 800-63B Rev 4). `steward deploy` formalizes the existing `dashboard-gen` + push loop into an explicit, reconciled deploy step, and is the entry point for the still-unbuilt `presenton-pixi-image` OpenShift and air-gap bundle targets. `steward provision` is a thin face over the pixi `[environments]` table and `scripts/bmad-loop-worktree` — provisioning what already exists a CLI call away, not a new environment-management system. `steward budget` starts honest and small: a documented ceiling plus a minimal check, growing into real enforcement only once there is live spend to meter.

## What Makes This Different

Steward's edge is not novel technology — every duty area has mature, well-adopted prior art (Backstage, Vault/Infisical, ArgoCD/Flux, Kubecost/Infracost; see the domain-research report). Its edge is fit: it is sized to a single-maintainer conda-forge factory, not an enterprise platform team, and it is built by cloning a packaging pattern (`pyforge-warden`'s `hatchling` + `pixi-build-python` pixi-workspace-member shape) that is already shipped, tested, and understood in this exact repo. The honest differentiator is dogfooding under real, already-dated incidents — Steward's first acceptance criterion is closing a leak that already happened, not a hypothetical one.

## Who This Serves

The sole user is this repo's own maintainer/factory operator, acting as the human behind every pyforge Crew persona (Marshal, Doctor, Atlas, Warden, Mason, Herald, Scribe) and every bmad-loop-driven autonomous session. This is internal, dogfooded tooling — there is no external customer, no multi-tenant concern, and no product-market question. Success for this user looks like: never re-discovering a credential leak after the fact again, never hand-running `dashboard-gen` + push again, and never wondering which pixi environment a new runner should provision into.

## Success Criteria

- The `JFROG_API_KEY` cross-host leak pattern is closed as a named, tested acceptance criterion of `steward keys` (not just documented as a known issue).
- `steward deploy` replaces the manual `dashboard-gen` + push sequence with a single reconciled command, with the same or better outcome.
- `steward provision --env <name>` correctly materializes any of the pixi estate's existing environments without the operator hand-running `pixi install -e <name>`.
- `steward budget` makes the "$1500/month locked" doctrine machine-readable (even if enforcement starts as a manual check) rather than leaving it as prose only.
- The package installs and runs the same way `pyforge-warden` does today (`pixi run -e pyforge-steward steward ...`), proving the packaging-pattern reuse held.

## Scope

**In for v1:** `steward keys` (host-scoped credential routing + Git-native at-rest secrets + risk-triggered rotation posture), `steward deploy` for the Pages dashboard specifically, `steward provision` over the existing pixi `[environments]` estate, `steward budget` as a documented-ceiling + minimal-check capability. Packaging as a `pyforge-warden`-pattern pixi workspace member (`src/shared/packages/pyforge-steward/`).

**Explicitly out for v1** (research-grounded non-goals, not deferred features):
- No standing Vault/Infisical-class secrets-manager service — `steward keys` is a thin wrapper over existing/lightweight tools, not a new server to operate and secure.
- No Backstage-class software catalog or scaffolder platform — `steward provision` is a CLI face over pixi, not a new IDP.
- No ArgoCD/Flux-class GitOps control plane — `steward deploy`'s reconciliation is a CLI-invoked step, not a standing controller.
- No Kubecost/OpenCost-class Kubernetes cost-allocation integration — there is no live Kubernetes cluster or cloud spend in this repo to allocate against yet.
- `presenton-pixi-image` on OpenShift and full air-gap bundle installs are named in the Dream as Steward's territory but are **not** committed for v1 — they remain the "frontier" the Dream itself calls unbuilt, and v1's `deploy` scope is the Pages dashboard only (see open question OQ3 below).

## Vision

If Steward succeeds, "no privilege outlives its deployment" stops being a motto and becomes a property the factory can point to — every credential Steward issues has a bounded scope and a bounded life, every deploy is a reconciled step instead of a manual push, and every new pixi environment or bmad-loop runner is a `steward provision` call away. Two to three years out, Steward is the station that lets the rest of the Crew (especially Marshal's autonomous loops) run genuinely unattended against production-adjacent surfaces (OpenShift, air-gapped installs) because the privilege and deployment boundary is provably tight, not just documented.

## Research Grounding

This brief is derived from two 2026-07-25 research reports (both tracked under `planning-artifacts/research/`): the domain-research report (comparable-tool landscape per duty, incident anchoring, epic-sequencing recommendation `keys → deploy → provision → budget`) and the technical-research report (packaging/architecture recommendations, cloning the `pyforge-warden` precedent). Both reports' `open_questions[]` are carried forward below rather than silently resolved.

## assumptions[]

- **A1**: Ran headless/express per the calling task's directive — elicitation gates in the underlying `bmad-product-brief` skill (Fast path vs. Coaching path choice, section-by-section review) were self-resolved rather than presented interactively.
- **A2**: The output workspace folder is named `brief-pyforge-steward-2026-07-25` rather than the literal `run_folder_pattern` substitution (`brief-{project_name}-{date}`), because `{project_name}` resolves globally to `local-recipes` (repo-level `_bmad/bmm/config.yaml`) even with `pyforge-steward` active as the per-project override — there is no `core.project_name` key in the project-layer `.bmad-config.toml` to shadow it. Using the literal resolved value would have produced a misleadingly-named folder for a pyforge-steward artifact; this is a deliberate, noted deviation, not a silent one.
- **A3**: This brief treats the pyforge maintainer as Steward's sole user (no external customer) per the Dream's own framing — not independently re-validated with the user this session.

## open_questions[]

(Carried forward from both research reports — PRD stage should resolve these, not this brief.)

- **OQ1 (budget scope)**: should `steward budget` ship as (a) documentation/doctrine-only, (b) a minimal manual-check CLI, or (c) be deferred entirely pending real cloud spend? This brief's Scope section leans (b); PRD should confirm.
- **OQ2 (keys implementation)**: does `steward keys` wrap SOPS+age directly, or a lighter Infisical-class API? Domain research leans SOPS+age (Git-native, matches this repo's "nothing committed, env-vars only" doctrine); PRD/architecture should confirm against Steward's actual secret inventory.
- **OQ3 (deploy v1 boundary)**: is `presenton-pixi-image` on OpenShift in scope for v1's `deploy` epic, or is v1 the Pages-dashboard formalization only (this brief's Scope section assumes the latter)? Materially affects `deploy` epic sizing.
- **OQ4 (Steward/Marshal provisioning boundary)**: does Steward's `provision` duty own bmad-loop runner provisioning itself, or only formalize what `scripts/bmad-loop-worktree` and the pixi `[environments]` table already do, leaving multi-project/worktree ownership with Marshal (per the Ecosystem Crew Dream's 2026-07-23 "Monorepo & Multi-Project Operation" assignment to Marshal)? The PRD must draw this boundary explicitly to avoid duty overlap.
- **OQ5 (CLI framework)**: Typer (2026 general best practice) or match whatever `pyforge-warden`'s `cli.py` actually uses? Technical research recommends reading Warden's `cli.py` directly before deciding — not yet done as of this brief.
- **OQ6 (deploy mechanism)**: for `steward deploy dashboard`, native GitHub Pages branch-based workflow (zero new Actions workflow) vs. a formal `upload-pages-artifact`/`deploy-pages` or `peaceiris/actions-gh-pages` Actions workflow for scheduled/push-button reconciliation? Both are valid 2026 patterns; left open for PRD/architecture.

*(All six were decided at the PRD stage as D1–D6 — see `prds/prd-pyforge-steward-2026-07-25/prd.md` §8; none is open today.)*

## Currency reconciliation — 2026-08-26

This brief is the v1 founding document and stays unrewritten above this line; every
present-tense claim above is dated 2026-07-25. Two newer research waves fired the
`research→brief` staleness edge and are folded in here, together with the as-built code
and the Unifying Strategy pack that now governs Steward's wider surface.

**From `research/market-steward-platform-ops-2026-08-08.md` (post-ship analogue pass):**

- Everything this brief scoped for v1 shipped — 18/18 stories, Epics 1–4, PRs #157, #291,
  #297, #302, #305 — and every refusal this brief's non-goals named (no standing
  secrets-manager service, no rotation scheduler, no provider revocation client, no cost
  SDK) is now **pinned by an invariant test**, not prose.
- The analogue comparison found Steward *ahead* of Vault-class tooling on exactly one
  axis — host-scoped egress gating of credentials (the JFrog-leak closure, FR-1/FR-7) —
  and honestly behind on exactly one — budget enforcement, where the Kubernetes lesson
  ("a quota without an admission point is documentation") still holds: `budget check`
  remains the honest `EXIT_BUDGET_NOT_CONFIGURED` stub because no metered spend source
  is wired yet.
- Of the three growth vectors it ranked: `provision --module` **shipped** (Epic 6,
  2026-08-09); a real spend meter behind `budget check` and runner *reaping* (its OQ1/OQ3)
  remain open, unforced by any incident.

**From the 2026-08-24 strategy research wave** (the four
`technical-pyforge-unifying-strategy-*-2026-08-24.md` files) **and the Unifying Strategy
pack** (`specs/spec-pyforge-unifying-strategy/`): the four-duty CLI this brief describes is
now a strict subset of the station. Steward owns the strategy — the Canopy host
(`src/platform/`), the shared chrome (`django-pyforge`, CAP-1), the Lane 1 CMS front door
(CAP-2), the eight-portal/MCP-face estate on the host ASGI (CAP-3/CAP-4), governed schema
change (CAP-9), and the query-plane through-line (CAP-19, minted and first-sliced
2026-08-26). As of 2026-08-26 the station's ledger reads **37/37 epics, 131/131 stories
done**, the eight stations are declared five-tier complete (Epic 37.1), and the strategy
SPEC's last three open questions were answered 2026-08-26 (`open_questions: []`).

**Deltas against this brief's own claims:**

- *Success criterion 2 ("`steward deploy` replaces `dashboard-gen` + push") was met, then
  deliberately outlived.* CAP-2 superseded the static Guildhall console; Story 30.2
  (2026-08-25) deleted the `dashboard-gen` generator and its 100+ inbound references.
  `steward deploy dashboard` survives as a reconciled diff+commit over `docs/dashboard/`
  (Kedro-Viz staging + stub) with a no-op build step; the live front door is Lane 1 `/`
  on the Canopy (CRC-proven 200, 2026-08-26).
- *"The 14-environment pixi estate"* is now a **27-environment** estate (root `pixi.toml`
  `[environments]`, counted 2026-08-26); `steward provision --env` still materializes any
  of them, and grew `--module`, `--list-modules`, and install-class judgment (Epics 6, 31).
- *The `age` pin this brief left implicit landed as a range*: `age = ">=1.3.1,<1.4"` in the
  package's `pixi.toml` run-dependencies, per the Warden NFR-C1 range-pin precedent.
- *The "frontier" this brief excluded from v1 (OpenShift, air-gap bundles) has since been
  built* — not under this brief, but under the station's later chains: the unified
  container (Epic 7), the vanilla Helm chart + OCP overlay and air-gap parity gate
  (Epic 12, `/ht/` 200 on CRC 2026-08-25), and the platform image (Epic 10). The
  deferral was correct at the time and is simply over.

Downstream currency lives in the PRD and architecture-spine reconciliations of this same
date; this brief needs no further maintenance unless the v1 record itself is contradicted.

## Currency reconciliation — 2026-08-31

`research/technical-pyforge-station-dossier-2026-08-30.md` (fleet-wide, all eight stations plus
`pyforge-core`, chain `pyforge-unifying-strategy` § Fleet conventions) fired `research→brief` again. It does not
contradict this brief's v1 record or either prior reconciliation above — one doc-drift finding is
worth recording because it lands on this exact brief's own subject:

- **The station README undercounts its own duties.** The dossier's §7 finding: Steward ships
  **thirteen** duties (`keys`, `deploy`, `provision`, `budget`, `sync`, `workspace`, `upgrade`,
  `suite`, plus a five-command bootstrap group) but the package README documents six — the same
  "written once near a milestone, never revisited" pattern the dossier found at every station that
  ships fast. This brief's own Success Criteria (line 30 above) are unaffected — they were written
  against the four v1 duties and all four still hold — but a README refresh is a legitimate,
  undersized follow-up the PRD/architecture layer has not picked up.
- **Confirms, does not revise**, two things the 2026-08-26 reconciliation above already stated:
  Steward owns Lane 1 `/console/` (the dossier independently arrives at "not a literal CMS," "zero
  status derivation of its own," matching this brief's CAP-2 framing exactly), and Doctor consumes
  Steward's fleet-scan output as a second status source (dossier §7 relationships list, confirming
  the ← Doctor edge already implied by this brief's CAP references).

No Scope, Success Criteria, or open-question change. `updated:` bumped to close the
`chain-currency-sweep` staleness edge; the v1 record above remains authoritative.

## Currency reconciliation — 2026-09-09

Fired by the `research→brief` staleness edge: `research/currency-review-pyforge-unifying-strategy-2026-09-09.md`
landed under this station's research folder (four parallel audits of the Unifying Strategy chain
against `main` `fe4025ea90`, every headline re-verified), and the brief's stamp sat at 2026-08-31.
Checked against this brief's mission and scope — **no change to Steward's charter.** The research
is chain-scoped to `spec-pyforge-unifying-strategy` (which Steward owns as the estate's post) and
was consumed the same day by `bmad-correct-course`: operator-approved
`sprint-change-proposal-2026-09-09-currency-review.md` minted **Epic 48** (the chain tells the
truth — the ledger syncer's `blocked` and missing-key guards, R-18..R-22 promoted out of the
deferred-work ledger, the CAP-axis namespace pass, the Single-Spec merge) and **Epic 49** (shipped
becomes in effect — a `verified:` line per capability, a doctor-owned advisory effect check, six
effect stories for CAP-4/-7/-11/-12/-14/-17). One operator ruling recorded upstream: the living
Dream's ≤400-line constraint is retired. Nothing here adds a capability to Steward the station;
the realization gate is a definition-of-done discipline the whole estate inherits, and its binding
home is the Spec's open question `realization-gate-home`.

## Currency reconciliation — 2026-09-14

Fired by the `research→brief` staleness edge again, and for the same structural reason as
2026-09-09: two research passes landed under this station's research folder on 2026-09-14 —
`research/technical-vocabulary-three-source-reconciliation-2026-09-14.md` (BMAD-METHOD v6.12.0
× the PyForge Lexicon × the Intelligence Hub / Frame-spec terms, three parallel read-only
passes at `main` `445976e5be`) and `research/technical-identifier-shapes-inventory-2026-09-14.md`
(nine identifier surfaces measured at the same head) — while this brief's stamp sat at
2026-09-09.

**No change to Steward's charter.** Both documents are **chain-scoped to
`vocabulary-one-name-one-job`**, both carry `status: draft`, and both state in their own
opening that they **take no decision**. They are Dream-tier inputs: `docs/dreams/vocabulary-one-name-one-job.md`
(`status: dreamt`, owner steward) cites them as its two sources, and
`planning-artifacts/specs/spec-vocabulary-one-name-one-job/` is where the contract will be
derived. Steward is the owning station because vocabulary and governance currency are its
post — which is exactly what this brief already says — so the research confirms the charter
rather than extending it.

**Two things from the passes worth carrying at brief altitude, because they bear on how
Steward measures anything:**

1. **The estate already has one identifier convention with zero exceptions** — `^### Story
   \d+\.\d+: .+$` holds 952/952 across all eight stations — and the doctor finding codes are
   the next cleanest at 124/124. The shapes pass exists because the *rest* of the surfaces
   are not like that. This is the measurement baseline any future standardization works
   against.
2. **The identifier sweep was run against a dirty working tree and says so, in bold, in its
   own method section** (36 modified paths, three `epics.md` files with uncommitted edits, one
   result materially affected). That caveat is the reason the document is usable: a
   measurement that names its own contamination can be re-run; one that does not gets adopted
   as a baseline and quietly poisons everything downstream. Recorded here as the standard this
   station holds research to, not as a defect in the pass.

**Nothing here adds a capability to Steward the station.** The vocabulary work is a chain with
its own Dream and its own Spec folder; this brief's scope, success criteria and vision are
unchanged.

## Currency reconciliation — 2026-09-25

`research→brief` edge: `research/technical-pyforge-unifying-strategy-bmad-method-whitepaper-2026-09-25.md`
landed while this brief sat at 2026-09-14.

**What it is and why the brief does not change.** The file keeps an operator-pasted whitepaper
whole and checks 18 of its claims against the installed BMAD skills (8 hold as stated). It is
chain-scoped to `pyforge-unifying-strategy`, declares `status: draft` and takes no decision; its
one strategic reading — the three BMAD execution modes are already this estate's session path,
`marshal factory dispatch` and the drains — is recorded in that Dream's 2026-09-25 consolidation,
not here. The same consolidation adds cutover capabilities (`fnd:CAP-12..15`) that Steward owns
as the cutover's through-line, which is already this brief's scope. Vision, users and success
criteria are unchanged.
