---
title: Product Brief — Steward
status: draft
created: 2026-07-25
updated: 2026-07-25
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
