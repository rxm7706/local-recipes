---
title: Steward — provision the line, hold the keys
type: dream
owner: steward
status: seeded
---

# Steward — the estate the factory stands on

## The Dream

The Provisioner's dream: **nothing the factory needs is missing, and nothing it
no longer needs stays privileged.** Mason ships artifacts and stops at the
registry; Doctor observes and prescribes; the Steward *deploys, provisions, and
operates* — environments and runners, service deployments, credential and
privilege lifecycles, resource budgets, and the incident response when the pager
goes off. Adopted 2026-07-23 when the ownership audit found Deployment &
Operations — the Implementation view's own stage, and the home of Privilege
Drift — orphaned between stations.

## What it owns

- **Provisioning**: bmad-loop runners, CI images, pixi environments — engines
  present before [[pyforge-doctor]]'s pre-flight ever runs.
- **Deployment**: services, not just artifacts — the Pages program console,
  [[presenton-pixi-image]] on OpenShift, [[enterprise-airgap]] bundle installs.
- **Keys**: credential issuance, scoping, rotation, revocation. First case on
  the desk: the `JFROG_API_KEY` unconditional-injection leak (Doctor finds,
  Steward remediates).
- **Budgets**: machine-readable resource ceilings ("locked at $1500/month") and
  their enforcement — the Taxonomy view's resource governance, operationalized.

## What is already Steward-shaped

- The Pages dashboard deploys (today: hand-run `dashboard-gen` + push — a
  Steward duty done manually).
- The pixi environment estate + `environment.yaml` sync discipline.
- The air-gap routing machinery ([[enterprise-airgap]]) awaiting an operator.

## Realization log

- **2026-07-23** — persona adopted into [[ecosystem-crew]] (crew 6 → 8);
  naming disambiguated from the [[fleet-stewardship]] practice Dream. CLI and
  chapter deck await their turns.
