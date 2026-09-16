---
title: Steward — provision the line, hold the keys
type: dream
owner: steward
status: realized
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

- **2026-07-23** — persona adopted into [[pyforge-charter]] (crew 6 → 8);
  naming disambiguated from the [[fleet-stewardship]] practice Dream. CLI and
  chapter deck await their turns.

- **2026-09-16 — The Guild environment: a minimal default for every agent
  and every harness (Dream-append-first; → `spec-pyforge-steward` CAP-5).**
  `local-recipes` was the right default when this repo was a recipe factory and
  nothing else. It is now 222 conda deps, 171 tasks and 10 GB on disk — and
  every agent (Claude, Cursor, Copilot, Gemini, a Cursor Cloud Agent in
  RXM-LOCAL-RECIPES, Marshal itself) is told to run the planning chain through
  it, so a cold cloud environment pays for grayskull, conda-smithy, the CFE
  atlas stack and the vulnerability databases to run `detectors-ci`. Measured
  today: of the 171 tasks, **48 are Guild/planning work** (the detectors, the
  ledger sync, the surface stamps, fleet-picture, the three preflight
  aggregates) and their scripts import exactly `pyforge.*`, `yaml`, `tomli`
  and `pixi_version_registry`; **86 are recipe-factory** (Mason's, they stay).
  The aspiration: **one small environment — `pyforge-guild` — that carries the
  current state of PyForge (core, doctor + its warden/testing-kit seam,
  marshal, steward) and nothing of the factory**, installs in under a minute
  from cold, is what `AGENTS.md`, `CLAUDE.md`, the Cursor rules, the station
  `SKILL.md`s and the cloud environment name as the default, and is the shape
  the foundry inherits (mode `rebuild`: B re-derives it from the same feature
  split). `local-recipes` keeps its name and every task by *including* the new
  feature, so nothing already written breaks; it becomes Mason's environment
  in fact, as it already is in practice. Scribe recall stays `-e pyforge-scribe`
  (cocoindex + graphify are heavy and already per-env). Kinships:
  [[marshal-token-economy]] (a cold 10 GB install is the largest fixed cost a
  cloud session pays before its first token), [[python-foundry-cutover]],
  [[pyforge-unifying-strategy]].

- **2026-09-16 — Frame draft re-grounding at `d7213c1` / `4596579`
  (Dream-append-first; → `spec-pyforge-steward` CAP-6; Frames remain
  [[intelligence-hub]] CAP-2's subject).** We adopted the frame-spec v0.3
  working draft on 09-14 from the head of openteams-ai/frame-spec#28. Since
  then #28 gained a 09-14 commit — *the draft carries no version number until
  a release assigns one*; its examples now read bare `type: frame` — and #29
  (81 commits, `spec/v0.3-validator`) landed a reference validator with
  composition fixtures, a `--self-check` that proves the draft agrees with its
  own element table, and **conformance profiles**, which §7 now makes a MUST
  for every implementation. Measured today, read-only: upstream's own
  `validate_frame.py` at #29's head passes all nine of our Frames (9/9, one
  INFO per station: `pyforge/company` is a qualified-ref), and `--self-check`
  passes the draft. So the adoption holds; what moves is *how we claim it*:
  (1) our `type: frame [0.3]` stamps a version that does not exist — we go
  bare, and the draft head we conform to is recorded as a **pin** in
  `docs/foundry/frames/README.md`, re-pinned by a memlog line whenever we
  re-ground; (2) PyForge's reader must **publish a conformance profile**
  (`docs/foundry/frames/conformance-profile.yaml`, the #29 YAML shape, checked
  by `--check-profile`) — today it reads Markdown only and resolves no
  composition, and says so; (3) §9 Security Considerations now bind the loader
  we have not built: a Frame is instructions, the source MUST be recorded
  beside the content, an untrusted source MUST NOT be loaded, and
  trust-every-source MUST be declared in the profile — these become
  acceptance criteria on the future Frame-into-agent-context work under
  [[marshal-token-economy]] `[context.wire]`, not an afterthought; (4) #29's
  composition fixtures (dedup keeps first, empty ≠ absent, style-clear) are
  the conformance tests for the day we compose station Frames with the Company
  Frame. Posture unchanged: we operate as if the current heads become v0.3;
  **no commits or comments to openteams-ai** — the validator is fetched to a
  temp dir at the pinned SHA by an opt-in task and never vendored. #28 stands
  at `CHANGES_REQUESTED`, 39 commits, mergeable, no LICENSE on `main` yet; the
  accepted-risk ledger entry stays open with today's date.

