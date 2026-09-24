---
id: SPEC-pyforge-marshal
spec: pyforge-marshal
status: ready
updated: "2026-09-24"
owner-dream: docs/dreams/pyforge-marshal.md
covers-dreams:
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/adaptive-model-tiering.md
  - docs/dreams/agent-portability.md
  - docs/dreams/agent-tool-surface.md
  - docs/dreams/agentic-sdlc-autonomy.md
  - docs/dreams/artifact-chain-reconciliation.md
  - docs/dreams/artifact-console.md
  - docs/dreams/bmad-611-era-alignment.md
  - docs/dreams/bmad-cursor-interactive-routing.md
  - docs/dreams/bmad-loop-baseline-drift.md
  - docs/dreams/bmad-loop-forward-dependency-blindness.md
  - docs/dreams/bmad-loop-intent-gap-work-preservation.md
  - docs/dreams/bmad-loop-liveness-footgun.md
  - docs/dreams/bmad-output-hygiene.md
  - docs/dreams/bmad-switch-scope-enforcement.md
  - docs/dreams/cursor-native-tier-map.md
  - docs/dreams/dashboard-project-path-derivation.md
  - docs/dreams/dashboard-velocity-captures-hand-driven-work.md
  - docs/dreams/dispatch-tier-routing-fails-safe.md
  - docs/dreams/dream-to-code-model-self-verification.md
  - docs/dreams/durable-runs.md
  - docs/dreams/factory-console.md
  - docs/dreams/fidelity-enforcement.md
  - docs/dreams/fleet-chain-completeness.md
  - docs/dreams/fleet-status-supervisor-fallback.md
  - docs/dreams/genesis-installer-name-retirement.md
  - docs/dreams/genesis-installer.md
  - docs/dreams/horizontal-run-concurrency.md
  - docs/dreams/landing-evidence-grammar.md
  - docs/dreams/library-catalog-manifest-sync.md
  - docs/dreams/loop-home-fleet-refresh.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - docs/dreams/marshal-drain-self-resolution.md
  - docs/dreams/marshal-land-cross-project-story-key-collision.md
  - docs/dreams/marshal-land-merge-subject.md
  - docs/dreams/marshal-launch-environment-integrity.md
  - docs/dreams/marshal-parallel-dispatch-fanout.md
  - docs/dreams/marshal-run-watch.md
  - docs/dreams/marshal-single-story-dispatch.md
  - docs/dreams/marshal-status-harness-run-id-poisoning.md
  - docs/dreams/marshal-templated-merge-subject-cross-project-collision.md
  - docs/dreams/marshal-token-economy.md
  - docs/dreams/one-front-door.md
  - docs/dreams/pr-lifecycle.md
  - docs/dreams/pyforge-core.md
  - docs/dreams/pyforge-marshal-loop-orchestrator.md
  - docs/dreams/pyforge-testing-charter.md
  - docs/dreams/quick-dev-reconciliation.md
  - docs/dreams/regenerable-factory.md
  - docs/dreams/risk-tiered-review-depth.md
  - docs/dreams/run-state-one-publisher.md
  - docs/dreams/spec-surface-overlap-tolerance.md
  - docs/dreams/sprint-status-auto-promote.md
  - docs/dreams/surface-drift-reconciliation.md
  - docs/dreams/token-economy-claude-session-path.md
surface:
  - src/shared/packages/pyforge-marshal/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_difficulty.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - .claude/tools/conda_forge_server.py
  - .claude/tools/gemini_server.py
  - .cursor/rules/bmad-build.mdc
  - .cursor/rules/bmad-build-auto.mdc
  - scripts/bmad_cursor_mdc_check.py
  - tests/scripts/test_bmad_cursor_mdc_check.py
  - pixi.toml
  - scripts/bmad_loop_baseline_drift_check.py
  - docs/dreams/bmad-loop-baseline-drift.md
  - .bmad-loop/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/
  - scripts/missing_preserve_check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py
  - docs/dreams/bmad-loop-liveness-footgun.md
  - scripts/bmad-switch
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - _bmad-output/projects/pyforge-herald/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-warden/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml
  - pyforge.doctor.sources.fleet_scan
  - docs/dashboard/index.html
  - docs/dashboard/data.js
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_tier_routing.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_retry.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_findings.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_spin.py
  - .claude/skills/conda-forge-expert/tests/meta/
  - docs/dashboard/README.md
  - docs/dashboard/kedro-viz/**
  - scripts/fleet_scan.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/planning.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
  - scripts/governance_currency_check.py
  - scripts/ad_citation_check.py
  - scripts/.ad-citation-baseline.json
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-core/
  - environment.yaml
  - docs/reference/library-llms-full.md
  - scripts/llms_full_check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_fleet_supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - _bmad-output/projects/*/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/tests/**/*watch*
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
  - .claude/skills/bmad-build-auto/step-04-review.md
  - .claude/skills/bmad-build-auto/spec-template.md
  - .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py
  - .claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py
  - .claude/skills/bmad-sprint-planning/references/generate-tracking.md
  - .claude/skills/bmad-sprint-planning/sprint-status-template.yaml
  - .claude/skills/bmad-retrospective/scripts/sprint_status.py
  - .claude/skills/bmad-retrospective/scripts/tests/test_sprint_status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/publisher.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/publish.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py
  - scripts/index_freshness_check.py
  - .claude/skills/bmad-build-auto/compile-epic-context.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_state.py
  - scripts/bmad-loop-worktree
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - scripts/promote_sprint_status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - scripts/.spec-surface-baseline.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py
surface-drift-exclude:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/published_plane.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/layer_savings_sources.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/refresh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_low_risk.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/structure_graph_dispatch_benchmark.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/model-ignores.gitignore.j2
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/publish.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/publisher.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_retry.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_findings.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_spin.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_tier_routing.py
  - docs/dashboard/kedro-viz/**
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-herald/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-warden/planning-artifacts/marshal-policy.toml
  - scripts/.spec-surface-baseline.json
companions:
  - glossary.md
  - extraction-manifest.md
  - ../../prds/prd-pyforge-marshal-2026-07-25/prd.md
  - ../../architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - ../../epics.md
sources:
  - ../../../../../../docs/dreams/pyforge-marshal.md
open_questions: []
---

> **Canonical contract.** Derived from `.memlog.md` and the folded Specs on 2026-09-16 (one-chain-per-station CAP-8). Do not hand-edit — append the memlog and re-derive.

# marshal CLI — one chain

## Why

A pain to solve and an opportunity to capture, on the same clock. The capability already exists and has already shipped real systems — the hand-assembled stack of an external orchestrator plus two shell-adjacent scripts drove one sibling project to 32/32 stories and another to 31/31 across six epics, running concurrent loop homes on one machine. What is missing is the product, and its absence is paid for by the operator in four specific ways: **the gate disappears exactly when it matters** (unattended is the mode that produces throughput, and it is the mode every available tool stops asking in); **unattended runs fail silently and expensively** (a dropped connection parks a session with no idle detection, burning to a token cap — three story attempts and a full review cycle lost in one wave, and separately 25.8M unrecoverable tokens to a session cap that killed a keystone story mid-work); **the paper trail evaporates** (of 31 story specs, 10 survived intact, 8 were zero-byte husks and 13 were gone entirely, all recoverable only by mining session transcripts — a sibling project lost 30 of 32 permanently); and **operating the loop is a set of memorized rules** written nowhere a machine can enforce them. Meanwhile the competitive slot is vacating rather than filling: every competitor trades away either the gate or the unattendedness, and nobody treats the spec as an executable contract. `marshal` is the harness — never a Skill — that turns that stack into a station: thin porcelain over the proven engine, **plus the supervisory layer the engine does not have**. The supervisor is the product.

## Capabilities

- **CAP-1 — loop homes and isolation** ← spec-pyforge-marshal CAP-1 (shipped 2026-09-09)
  - **intent:** An operator can create an isolated, policy-composed, preflight-verified place for a loop to run, and prove that several of them are genuinely isolated.
  - **success:** One idempotent command yields a loop home whose active-project marker and planning symlinks agree, whose Tier-3 store resolves to the same canonical realpath as the main checkout, and which never replaces a real non-empty local directory; an isolation assertion over N ≥ 2 homes exits 0 only when markers and symlinks are independent, Tier-3 realpaths identical and the main checkout untouched; preflight exits non-zero naming every blocking finding (harness version, multiplexer backend, adapter binary, resolvable story feed, resolvable verify commands, `main` not checked out twice, unacknowledged adapter first-run requirement) rather than discovering them at minute 90; teardown removes worktree and branch, refuses on uncommitted or unmerged work absent an explicit flag, and never touches the canonical store.
- **CAP-2 — supervised unattended runs** ← spec-pyforge-marshal CAP-2 (shipped 2026-09-09)
  - **intent:** An operator can launch or resume a gated run against an approved spec and have it watched from outside by something the session cannot disable — so a run either completes, escalates, or stops with a named reason.
  - **success:** Launch and resume return a run identifier promptly and survive the caller exiting; a session that stops producing output is detected from externally observable evidence and acted on through a journaled nudge → stop-and-retry → defer ladder well before any token or time cap; per-story and per-run ceilings stop the unit with a named reason and a prior warning, never a silent defer; an escalation pauses the run so no story proceeds past it, is journaled with story key, reason and the artifact needing a decision, and fires at least a durable file marker; a resume against an unresolved escalation is refused with a named finding; and the run journal is written incrementally, so a killed run still has a journal up to the kill.
- **CAP-3 — gates you can run** ← spec-pyforge-marshal CAP-3 (shipped 2026-09-09)
  - **intent:** An operator or CI can evaluate the gate standalone — with no run in flight — and get a verdict that never false-greens.
  - **success:** Evaluation runs the project's configured verify commands, reports pass/fail per command with captured output, never mutates the working tree, and projects to a stable exit contract (0 pass, non-zero fail, a distinct code for could-not-evaluate); the scope check names each offending path and, for a frozen-file violation, the story that froze it; a story whose declared deliverable is a document or decision record is classified before verification and does not fail on "no changes in worktree"; the gate mode carries its autonomy label at launch and in the journal, and a mid-run change is recorded as a timestamped decision; every evaluation leaves a durable record of commands, exit codes, scope verdict, tree revision and timestamp; and a sound-but-unconverged story can be landed deliberately only after the full gate re-runs.
- **CAP-4 — landing with a durable paper trail** ← spec-pyforge-marshal CAP-4 (shipped 2026-09-09)
  - **intent:** An operator can land a wave and have every merged story's spec survive teardown, without anyone remembering to copy a file.
  - **success:** Every merged story's spec is promoted from run scratch into the tracked archive **before** any code path may remove that story's worktree, and is only counted promoted when its bytes are reachable from a ref that survives the loop home; a zero-byte or truncated source is reported as a paper-trail gap and never promoted over a good copy; a merged story with no promotable spec is reported, never passed over; missing specs yield ordered recovery search paths with any regenerated contract-only spec labelled as such; one batch pull request is opened or updated (never duplicated) against the configured base with per-story gate verdicts in the body; merge subjects render from the configured template that the same module parses to verify conformance; sprint and console surfaces refresh with ledger-versus-git discrepancies reported rather than silently resolved; re-running after a partial failure completes only the remaining steps, reporting each as done/skipped/failed; and nothing Marshal emits carries an AI-attribution trailer or courtesy preamble.
- **CAP-5 — fleet visibility** ← spec-pyforge-marshal CAP-5 (shipped 2026-09-09)
  - **intent:** An operator can see every loop home at once, derived from ledgers rather than a hand-maintained file, with anything needing a human surfaced first.
  - **success:** One row per home carrying project, branch, state (idle / running / paused-on-escalation / stopped), current story, elapsed time and budget consumed, with paused-on-escalation rows visually distinguished and sorted to the top carrying their reason and the artifact needing a decision; drilling into a run shows the story sequence with per-story gate verdicts, escalations, deferrals and consumption; a story marked done with no corresponding merge — and the converse — is reported as a named discrepancy; and every human view has a machine-readable counterpart under a versioned schema a console or dashboard consumes without scraping.
- **CAP-6 — portability proven, not claimed** ← spec-pyforge-marshal CAP-6 (shipped 2026-09-09)
  - **intent:** An operator can run the method on an agent other than the one it was built on, and hold a dated artifact proving it rather than a support table asserting it.
  - **success:** After projection, every configured adapter's declared skill tree contains the project's skills, the mechanism used is reported, the canonical source tree stays authoritative and re-projection converges with stale entries removed; drift detection reports added/removed/modified per tree and runs in preflight for non-default adapters, with a check that is mechanism-specific and can actually fail; a probe records binary presence, version, declared capabilities and probe output with sensitive values redacted, reporting an absent adapter as unavailable rather than failing; a canonical smoke story exercising spec → change → verify → commit runs in a throwaway home and leaves no residue; results accumulate into a dated matrix distinguishing not-attempted from unavailable from fail, where **only `pass` counts**; the cross-tool instruction-file family is checked for mutual drift and **reported, never edited**; and each adapter's first-run requirement plus sustained-automation caveat is acknowledged once, with unacknowledged adapters a blocking preflight finding.
- **CAP-7 — policy composition** ← spec-pyforge-marshal CAP-7 (shipped 2026-09-09)
  - **intent:** An operator's memorized operating rules become layered configuration a machine enforces, with every effective value traceable to the layer that set it.
  - **success:** Composition is pure — the same inputs produce the same output — and materializes once into the loop home; the effective policy prints each key with its winning layer and secrets redacted; project-specific values come from the project layer so switching projects requires editing no shared file and the worktree-seed path list is generated rather than literal; a story's declared difficulty selects per-stage models with no between-batch config edit, and the resolved model is journaled per story; an invalid composed policy is rejected at preflight naming the layer that introduced each bad key; and an architectural test fails the build if any module other than the single seam touches the harness.
- **CAP-8 — one install yields the whole stack** ← spec-pyforge-marshal CAP-8 (shipped 2026-09-09)
  - **intent:** Marshal ships the way the rest of the Guild ships, and installing it brings the engine with it — the operative half of the wrap decision.
  - **success:** The distribution is `pyforge-marshal`, module `pyforge.marshal`, console script `marshal`, living in the repo's shared packages workspace, importable from a clean environment install; a conda package declaring the harness as a run dependency pinned to the supported range, plus a wheel and sdist from the same source tree, yield a working `marshal --help` and `marshal --version` reporting both Marshal's and the resolved harness's versions into every run's journal, with an out-of-range harness a prominent warning and a blocking preflight finding on a major mismatch; and a tracked register lists each upstream-shaped gap with its Marshal workaround and upstream status, seeded with idle-strand detection, per-story model tiering, `planning_artifacts` composition, ACP evaluation and non-POSIX multiplexer support, each naming the capability that compensates while the gap is open.
- **CAP-9 — the last mile lands itself** ← spec-pyforge-marshal CAP-9 (shipped 2026-09-09)
  - **intent:** An operator's finished wave lands on `main` without a human driving the last mile — the landing rules declared once as policy, executed and refused deterministically, with the same supervisor/journal/verdict triad every other stage already has.
  - **success:** Landing rules — required checks, merge strategy, label rules (including repo-specific ones like this fork's `maintenance` label and its ungated env-sync trigger), branch retirement, and resync — compose from the policy layers with per-key provenance; `marshal land` opens or updates the PR, applies labels, waits on required checks, merges, retires the branch and resyncs — idempotently and re-entrantly, so a half-landed story (PR open, checks green, merge never issued) converges on re-run; refusal semantics mirror teardown: no merge on a red required check, no merge past an unacknowledged advisory finding, no silent force; every landing leaves a journal verdict recording which checks were required, which passed, what merged, and under whose authority; and wrap-never-absorb is carried unchanged — the engine keeps dev/verify/review/commit and deliberately leaves this gap open; Marshal fills it around the engine.
- **CAP-10 — operating model as data** ← spec-pyforge-marshal CAP-10 (shipped 2026-09-09)
  - **intent:** A maintainer can declare the operating model as data — every artifact in exactly one class — so adding a model artifact never requires touching engine code.
  - **success:** A coverage check HARD-fails when any known artifact carries no class (deferral is an explicit enumerated state, not a gap); `marshal seed explain <artifact>` prints that artifact's class, rationale, and update behavior; adding an artifact to the model is provably a manifest-only diff.
- **CAP-11 — managed-region upgrades** ← spec-pyforge-marshal CAP-11 (shipped 2026-09-09)
  - **intent:** An operator can carry the model's rule text inside files their team writes freely, and have only that text upgrade.
  - **success:** An update replaces only the marked span, byte for byte, leaving the rest of the file identical; a hand-edit inside the span is detected by body hash and reported; deleting the markers is recorded as a permanent opt-out that later runs respect; nested or overlapping regions are rejected with a specific error; no run can produce a conflict marker.
- **CAP-12 — adopt onto a living repo** ← spec-pyforge-marshal CAP-12 (shipped 2026-09-09)
  - **intent:** A team can layer the model onto a repository that already builds and ships, reviewing exactly what will change before anything is written.
  - **success:** `marshal seed adopt` runs detect → plan → confirm → apply, dry-run by default and completing in under 10 seconds on a `local-recipes`-sized repo, emitting a machine-readable plan naming each artifact's path, class, detected state, proposed action, and rationale; against `local-recipes` at the shipped model version the plan is **empty**; a second run on an unchanged repo is likewise empty and writes nothing; it refuses on a hand-edited managed artifact and on a dirty git worktree; a `present-legacy` artifact is recorded and preserved, never modified or deleted; and paths passed to `--skip` are recorded and honored on every later run.
- **CAP-13 — seed check in CI** ← spec-pyforge-marshal CAP-13 (shipped 2026-09-09)
  - **intent:** An installed repo can prove in CI that it still conforms to the model.
  - **success:** `marshal seed check` is read-only with writes structurally unreachable, exits non-zero on any HARD finding, emits typed stable findings each carrying a documented remedy, supports `--json` for CI annotation, reports the repo's model version against the bundled one, and completes offline in under 5 seconds on a `local-recipes`-sized repo.
- **CAP-14 — seed init a Dream-first repo** ← spec-pyforge-marshal CAP-14 (shipped 2026-09-09)
  - **intent:** A maintainer can create a new repository already born Dream-first, rather than assembling the model by hand.
  - **success:** `marshal seed init <path>` yields a tree with the tier layout, one seeded Dream conforming to the Tier-0 frontmatter contract, the BMAD multi-project subtree and its `PROJECTS.md` row, the `.gitignore` model region, the selected agent adapters, and the detector wired into CI — after which `marshal seed check` is green, offline, with zero network calls, in under five minutes wall-clock; `init` refuses a non-empty directory without `--force`, directing the operator to `adopt`.
- **CAP-15 — seed update without touching team work** ← spec-pyforge-marshal CAP-15 (shipped 2026-09-09)
  - **intent:** An already-installed repository can take a later version of the model without hand edits, and without the upgrade being able to reach the team's own work.
  - **success:** `marshal seed update` writes a plan and changes nothing until `--run`; a simulated breaking model change (v1 → v2) is absorbed by a version-ordered, applied-once migration with no manual edits; `copied-seeded` artifacts are *offered*, never imposed; and an attempted write to any never-write path is a hard error asserted by test.
- **CAP-16 — adapters from one contract** ← spec-pyforge-marshal CAP-16 (shipped 2026-09-09)
  - **intent:** Every per-tool agent entry point in an installed repo derives from one contract, so they cannot drift apart.
  - **success:** The four V1 adapters (`CLAUDE.md`, `.cursor/rules/specs.mdc`, `.github/copilot-instructions.md`, `GEMINI.md`) render from a single neutral-contract source; adding a fifth is a manifest entry plus a wrapper template with no engine change; an adapter file that already exists with repo-specific content receives the model as a managed region rather than an overwrite.
- **CAP-17 — genesis-owned state file** ← spec-pyforge-marshal CAP-17 (shipped 2026-09-09)
  - **intent:** A repo carries a legible record of what Genesis owns in it and what it has already done.
  - **success:** One git-tracked, schema-validated, do-not-hand-edit state file records `model_version`, `genesis_version`, mode, adopted/updated timestamps, `agents[]`, `managed[]` (path + class + content hash), `skips[]`, `legacy[]`, and `migrations_applied[]`; an invalid file surfaces as a `state-invalid` finding rather than a crash; state is written last, after every file write succeeds, in one atomic replace.
- **CAP-18 — air-gap by construction** ← spec-pyforge-marshal CAP-18 (shipped 2026-09-09)
  - **intent:** An air-gapped or firewalled team can install and operate the model with no egress.
  - **success:** An egress-counter test asserts zero network calls across `init`, `adopt --dry-run`, `adopt --apply`, and `check`; the only reachable network path is an explicit `--template <url>`; every runtime dependency resolves from conda-forge or an internal mirror.
- **CAP-19 — from spec-adaptive-model-tiering** ← spec-adaptive-model-tiering CAP-1 (shipped 2026-09-16)
  - **intent:** A project's `model_tier_map`, once populated with real `{difficulty:
  - **success:** Given a project with a populated `model_tier_map` and an in-scope story
- **CAP-20 — from spec-adaptive-model-tiering** ← spec-adaptive-model-tiering CAP-2 (shipped 2026-09-16)
  - **intent:** A story showing it is genuinely struggling (repeated dev attempts, repeated
  - **success:** Given a story that exhausts an attempt/cycle threshold, its next attempt runs
- **CAP-21 — one governed surface** ← spec-agent-tool-surface CAP-1
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-22 — the surface survives a clone** ← spec-agent-tool-surface CAP-2
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-23 — CLI ⇄ tool parity is gated, not reviewed** ← spec-agent-tool-surface CAP-3
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-24 — coverage is measured, not assumed** ← spec-agent-tool-surface CAP-4
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-25 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-1 (shipped 2026-09-09)
  - **intent:** Operator can start the judgment audit on a mechanically clean
  - **success:** Six detectors + meta-suite green; zero `[drift-presumed]`
- **CAP-26 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-2 (shipped 2026-09-09)
  - **intent:** Every one of the 68 remaining stories (steward 4 → mason 28 →
  - **success:** 68/68 verdict rows, each with `file:line` or command-output
- **CAP-27 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-3 (shipped 2026-09-09)
  - **intent:** All five completed stations (atlas, doctor, herald, scribe,
  - **success:** Per-station gate report; every chain column verified or
- **CAP-28 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-4 (shipped 2026-09-09)
  - **intent:** The TEA column is refreshed by measurement: per-epic
  - **success:** Coverage table present per epic in the gate reports.
- **CAP-29 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-5 (shipped 2026-09-09)
  - **intent:** Audit verdicts become repairs in both directions: artifact
  - **success:** Every fix traceable to a verdict row and an owning-skill or
- **CAP-30 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-6 (shipped 2026-09-09)
  - **intent:** Each of the four queued decomposition chains (atlas → herald →
  - **success:** Every decomposition PR cites the landed gate report it builds
- **CAP-31 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-7 (shipped 2026-09-09)
  - **intent:** Operator can make the resume decision on measured artifacts:
  - **success:** Baseline stamped; board matches ledger; the 68-story
- **CAP-32 — from spec-artifact-chain-reconciliation** ← spec-artifact-chain-reconciliation CAP-8 (shipped 2026-09-09)
  - **intent:** The non-station estate is audited too: every Dream in
  - **success:** 61/61 Dreams dispositioned in an inventory gate report.
- **CAP-33 — Retired-ID purge + regression guard** ← spec-bmad-611-era-alignment CAP-1
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-34 — bmad-loop skill refresh** ← spec-bmad-611-era-alignment CAP-2
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-35 — Memlog-format migration** ← spec-bmad-611-era-alignment CAP-3
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-36 — Policy-surface parity** ← spec-bmad-611-era-alignment CAP-4
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-37 — 0.11 status vocabulary** ← spec-bmad-611-era-alignment CAP-5
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-38 — Deferred-work intake reads both sources** ← spec-bmad-611-era-alignment CAP-6
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-39 — Living factory docs re-grounded, with a named owner** ← spec-bmad-611-era-alignment CAP-7
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-40 — 6.12 retired-ID roster** ← spec-bmad-611-era-alignment CAP-8
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-41 — Project-context surface follows 6.12** ← spec-bmad-611-era-alignment CAP-9
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-42 — Documentation pointers follow 6.12** ← spec-bmad-611-era-alignment CAP-10
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-43 — bmad-loop 0.11.1 parity, durable** ← spec-bmad-611-era-alignment CAP-11
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-44 — Every live caller follows the shim retirement** ← spec-bmad-611-era-alignment CAP-12
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-45 — TEA adoption is marshal Epic 31 (relay)** ← spec-bmad-611-era-alignment CAP-13
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-46 — The live subagent probe** ← spec-bmad-cursor-interactive-routing CAP-1
  - **intent:** settle, empirically, whether Cursor's interactive IDE chat surface (not the
  - **success:** a dated, reproducible probe result recorded in this Spec's memlog — pass or fail,
- **CAP-47 — `.mdc` routing layer** ← spec-bmad-cursor-interactive-routing CAP-2
  - **intent:** a `.cursor/rules/*.mdc` file per BMAD skill (or one generated router), mechanically
  - **success:** a request typed into Cursor's interactive chat surfaces and runs the identical
- **CAP-48 — The honest fallback** ← spec-bmad-cursor-interactive-routing CAP-3
  - **intent:** `bmad-build-auto`'s workflow HALTs `blocked`/`no subagents` exactly as designed
  - **success:** no skill silently degrades its review discipline inside Cursor chat.
- **CAP-49 — Team-memory reachability** ← spec-bmad-cursor-interactive-routing CAP-4
  - **intent:** `.claude/memory/` content reachable from Cursor chat via whatever reference
  - **success:** `Read` of `.claude/memory/MEMORY.md` works. There is no Claude Code `@path`
- **CAP-50 — from spec-bmad-loop-baseline-drift** ← spec-bmad-loop-baseline-drift CAP-1 (shipped 2026-09-09)
  - **intent:** A Marshal-side detector at the adapter seam — reading only feeds `bmad_loop`
  - **success:** Replaying run `20260813-094919-bfcb`'s journal (story 9-6) fires the detector
- **CAP-51 — from spec-bmad-loop-baseline-drift** ← spec-bmad-loop-baseline-drift CAP-2 (shipped 2026-09-09)
  - **intent:** This defer reason can no longer pass silently — loud-defer containment. The
  - **success:** A future occurrence is surfaced by the containment within its watch window with
- **CAP-52 — from spec-bmad-loop-baseline-drift** ← spec-bmad-loop-baseline-drift CAP-3 (shipped 2026-09-09)
  - **intent:** The drafted upstream issue already in the Dream (lines ~125–201: journal timeline,
  - **success:** Both gates recorded as checked; then either the issue is filed (URL appended to
- **CAP-53 — every station's structured epics doc is swept for forward-epic `** ← spec-bmad-loop-forward-dependency-blindness CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-54 — a found forward-dependent story is set to a non-actionable status** ← spec-bmad-loop-forward-dependency-blindness CAP-2 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-55 — a permanent detector prevents recurrence** ← spec-bmad-loop-forward-dependency-blindness CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-56 — an unparseable epics format is reported honestly, never silently passed** ← spec-bmad-loop-forward-dependency-blindness CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-57 — gated story loops** ← spec-bmad-loop-governance CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-58 — concurrent loop homes** ← spec-bmad-loop-governance CAP-2 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-59 — model tiering as policy** ← spec-bmad-loop-governance CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-60 — every run visible** ← spec-bmad-loop-governance CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-61 — from spec-bmad-loop-intent-gap-work-preservation** ← spec-bmad-loop-intent-gap-work-preservation CAP-1 (shipped 2026-09-09)
  - **intent:** Preservation symmetry -- before/around an intent-gap revert discards tracked
  - **success:** After an intent-gap halt on a story with tracked changes, a preserve artifact
- **CAP-62 — from spec-bmad-loop-intent-gap-work-preservation** ← spec-bmad-loop-intent-gap-work-preservation CAP-2 (shipped 2026-09-09)
  - **intent:** The escalation surface names the artifact -- the "Auto Run Result" / escalation
  - **success:** Given only the escalation text of a post-fix intent-gap halt, `bmad-loop
- **CAP-63 — from spec-bmad-loop-intent-gap-work-preservation** ← spec-bmad-loop-intent-gap-work-preservation CAP-3 (shipped 2026-09-09)
  - **intent:** A post-hoc detector makes any residual gap loud -- an intent-gap halt whose
  - **success:** Simulating an intent-gap halt with no preserve artifact trips the detector;
- **CAP-64 — Marshal gains the missing liveness primitive** ← spec-bmad-loop-liveness-footgun CAP-1
  - **intent:** A Marshal-side primitive answers "is run X's engine alive?" by consuming
  - **success:** Given a live run, a stopped run, and an absent/unreadable run directory,
- **CAP-65 — The operator answer is one command** ← spec-bmad-loop-liveness-footgun CAP-2
  - **intent:** The operating instructions this repo hands out (the fleet landing-pass
  - **success:** No tracked operator instruction prescribes `cat engine.pid` /
- **CAP-66 — An UNSUPERVISED row has a cheap double-check** ← spec-bmad-loop-liveness-footgun CAP-3
  - **intent:** For a run Marshal did not spawn (a raw `bmad-loop run`/`resume` with no
  - **success:** Reproducing the Dream's 2026-08-15 scenario (raw `bmad-loop run`, no
- **CAP-67 — dead test-scaffolding archival** ← spec-bmad-output-hygiene CAP-1 (shipped 2026-09-16)
  - **intent:** `git mv` `tests/`, `pytest.ini`, and `playwright.config.ts` out
  - **success:** None of the 7 station roots contain these paths; each exists
- **CAP-68 — hollow `sprint-status.yaml` archival** ← spec-bmad-output-hygiene CAP-2 (shipped 2026-09-16)
  - **intent:** `git mv` the dead, identical-shape `planning-artifacts/sprint-status.yaml`
  - **success:** File absent from its original path in all 9 projects, present
- **CAP-69 — Genesis `test-architecture.md` fix** ← spec-bmad-output-hygiene CAP-3 (shipped 2026-09-16)
  - **intent:** Regenerate Genesis's `test-architecture.md` — the one station the
  - **success:** The file makes no claim contradicted by Genesis's own current
- **CAP-70 — README placeholder fill** ← spec-bmad-output-hygiene CAP-4 (shipped 2026-09-16)
  - **intent:** The literal `[role]`/`[responsibilities]` placeholders actually
  - **success:** No station README contains a literal `[role]` or
- **CAP-71 — orphaned single-file archival** ← spec-bmad-output-hygiene CAP-5 (shipped 2026-09-16)
  - **intent:** `git mv` Atlas's `RESUME-EPIC-10.md` and Herald's
  - **success:** Both files exist under their mirrored `archive/` path, are
- **CAP-72 — `project-context.md` drift fix** ← spec-bmad-output-hygiene CAP-6 (shipped 2026-09-16)
  - **intent:** Regenerate Mason's and Herald's `project-context.md` in place
  - **success:** Both files' claimed counts match `sprint-status-ledger.yaml`;
- **CAP-73 — `PROJECTS.md` Dream-pointer fix** ← spec-bmad-output-hygiene CAP-7 (shipped 2026-09-16)
  - **intent:** In `_bmad-output/PROJECTS.md`'s Projects table, repoint mason's
  - **success:** Both pointers resolve to an existing `type: dream` file that is
- **CAP-74 — marshal-brief layout fix** ← spec-bmad-output-hygiene CAP-9 (shipped 2026-09-16)
  - **intent:** `product-brief-pyforge-marshal.md` is marshal's genuine, sole
  - **success:** File lives at the sharded path; no remaining reference to the
- **CAP-75 — from spec-bmad-switch-scope-enforcement** ← spec-bmad-switch-scope-enforcement CAP-1
  - **intent:** One shared verification primitive — `verify_scope(root, expected_slug) -> None |
  - **success:** With marker and both symlinks all pointing at slug B, `verify_scope(root, "A")`
- **CAP-76 — from spec-bmad-switch-scope-enforcement** ← spec-bmad-switch-scope-enforcement CAP-2
  - **intent:** BOTH existing guards are replaced by consumption of the primitive —
  - **success:** Exactly one implementation of the triangle check exists in the repo; both callers
- **CAP-77 — from spec-bmad-switch-scope-enforcement** ← spec-bmad-switch-scope-enforcement CAP-3
  - **intent:** Drift is a hard failure everywhere. `bmad-switch --current` exits non-zero on
  - **success:** On a deliberately desynced tree, `scripts/bmad-switch --current` exits non-zero
- **CAP-78 — from spec-cursor-native-tier-map** ← spec-cursor-native-tier-map CAP-1
  - **intent:** All eight stations' `model_tier_map` easy/medium/heavy
  - **success:** `parse_stage_entry` on each stage yields
- **CAP-79 — from spec-cursor-native-tier-map** ← spec-cursor-native-tier-map CAP-2
  - **intent:** The fail-safe stays: a Cursor-catalogued model is never
  - **success:** Existing provider-mismatch tests remain green.
- **CAP-80 — one resolver, one override table** ← spec-dashboard-project-path-derivation CAP-1
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-81 — `PROJECT_SOURCES` is derived, not declared** ← spec-dashboard-project-path-derivation CAP-2
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-82 — resolution ships in `data.js`; the JS never re-derives** ← spec-dashboard-project-path-derivation CAP-3
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-83 — an unresolvable slug fails loud** ← spec-dashboard-project-path-derivation CAP-4
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-84 — wall-clock fallback derivation** ← spec-dashboard-velocity-captures-hand-driven-work CAP-1 (shipped 2026-09-09)
  - **intent:** The dashboard generator derives a wall-clock duration for every `done` story
  - **success:** After a local generate, doctor's 8.1–8.4 carry timing marks derived from
- **CAP-85 — fidelity is visible, never blended** ← spec-dashboard-velocity-captures-hand-driven-work CAP-2 (shipped 2026-09-09)
  - **intent:** A wall-clock-derived mark is visually and textually distinguished from
  - **success:** On a line mixing both classes, a reader can tell each story's metric class
- **CAP-86 — the coverage caption partitions by true reason** ← spec-dashboard-velocity-captures-hand-driven-work CAP-3 (shipped 2026-09-09)
  - **intent:** The coverage statement stops lumping every unmeasured story under "predates
  - **success:** For a line containing hand-driven stories, the rendered caption names each
- **CAP-87 — from spec-dispatch-tier-routing-fails-safe** ← spec-dispatch-tier-routing-fails-safe CAP-1 (shipped 2026-09-12)
  - **intent:** The tier-routing resolver never writes a dev/review stage model override
  - **success:** A synthetic fixture whose `model_tier_map` stage candidate names a model
- **CAP-88 — from spec-dispatch-tier-routing-fails-safe** ← spec-dispatch-tier-routing-fails-safe CAP-2 (shipped 2026-09-12)
  - **intent:** Fleet-wide, `model_tier_map`'s heavy/medium/easy `dev`/`review` entries
  - **success:** Re-running the same direct `resolve_tier_launch` / `render_policy_toml`
- **CAP-89 — from spec-durable-runs** ← spec-durable-runs CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-90 — from spec-durable-runs** ← spec-durable-runs CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-91 — from spec-durable-runs** ← spec-durable-runs CAP-5 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-92 — from spec-durable-runs** ← spec-durable-runs CAP-6 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-93 — local status sync** ← spec-factory-console CAP-1 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-94 — hands-off CI refresh** ← spec-factory-console CAP-2 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-95 — Dreamscape scan** ← spec-factory-console CAP-3 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-96 — stable data contract** ← spec-factory-console CAP-4 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-97 — from spec-fidelity-enforcement** ← spec-fidelity-enforcement CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-98 — from spec-fidelity-enforcement** ← spec-fidelity-enforcement CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-99 — from spec-fidelity-enforcement** ← spec-fidelity-enforcement CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-100 — from spec-fidelity-enforcement** ← spec-fidelity-enforcement CAP-6 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-101 — from spec-fidelity-enforcement** ← spec-fidelity-enforcement CAP-9 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-102 — orchestrated chain regeneration** ← spec-fleet-chain-completeness CAP-1
  - **intent:** From a consolidated Dream, run the full planning chain in sequence via
  - **success:** a single invocation against a consolidated Dream produces a coherent
- **CAP-103 — code-status preservation** ← spec-fleet-chain-completeness CAP-2
  - **intent:** Regenerating the planning chain does not clobber existing Code implementation
  - **success:** re-running the workflow against an already-partially-implemented project
- **CAP-104 — chain-completeness audit mode** ← spec-fleet-chain-completeness CAP-3
  - **intent:** A verify-only pass, independent of regeneration, answers whether a project's
  - **success:** run in audit mode against any of the 8 PyForge stations and get a pass/fail
- **CAP-105 — orphan detection with review-gated cleanup** ← spec-fleet-chain-completeness CAP-4
  - **intent:** Identify artifacts the regenerated chain no longer references — old spec
  - **success:** after a consolidation run, the operator sees a named orphan manifest
- **CAP-106 — configurable per-project invocation** ← spec-fleet-chain-completeness CAP-5
  - **intent:** `project_slug`, `dream_path`, `chain_mode` (`full` default | `minimal`),
  - **success:** the same workflow definition runs unmodified against any of the 8 stations by
- **CAP-107 — The operating-model standard is 6.12-accurate, and derives what it can** ← spec-fleet-consistency-standard CAP-1 (shipped 2026-09-09)
  - **intent:** A reader of the standard can trust every skill name, script path and file reference in it, and the parts that restate machine-readable facts are gone rather than maintained by hand.
  - **success:** `EXEMPLAR-STANDARD.md` names no skill, script or path that does not resolve on disk; its 16-stage skill-mapping table and its dated conformance-status snapshots are removed (the first restates BMAD's own skill set, the second is a hand-derived measurement a detector produces); INV-0..INV-5, the eleven-row conformance table, the kernel/companion rule and the provenance rules survive intact; the file keeps its path, because `pixi.toml`'s `dream-chain` detector names it as its `Contract:`.
- **CAP-108 — One test-suite vocabulary across the fleet** ← spec-fleet-consistency-standard CAP-2 (shipped 2026-09-09)
  - **intent:** A test file's directory tells any reader and any tool which suite it belongs to, using the same three names at every station.
  - **success:** Every station's tests resolve to `unit/`, `integration/` or `meta/` (plus a non-collected `fixtures/`, and `conftest.py` at the tests root); `conformance/`, `contract/`, `oracle/` and the loose root-level test files are gone; `marshal/support/` is renamed `_support/` so it stops matching suite globs; `run_station_coverage_gate.py`'s suite map needs no per-station special case; and each station's own suite passes after its move.
- **CAP-109 — No artifact survives that the toolchain no longer produces** ← spec-fleet-consistency-standard CAP-3 (shipped 2026-09-09)
  - **intent:** The planning tree contains only artifacts something still generates or a human still maintains, so a reader never has to guess whether a stale file is authoritative.
  - **success:** All eight `epics-with-stories.md` are retired, their normative content rehomed first (steward's suite-shape mandate at `epics-with-stories.md:61` is known; the other seven are audited before deletion); the four code references are removed (`hygiene_definitions.py` allowlist entry, `deps.py` and `dispatch_fleet.py` exclusions, `bmad_tea_playwright.py` fallback); no station README still points at one.
- **CAP-110 — Artifact naming is machine-classifiable** ← spec-fleet-consistency-standard CAP-4 (shipped 2026-09-09)
  - **intent:** Every planning artifact matches the classifier that governs it, so pointing a detector at a new station reports real findings rather than false `uncovered` noise.
  - **success:** Every `implementation-readiness-report-*` uses the hyphenated ISO form `bmad_drift_check.py` matches; `bmad-drift` reports zero `uncovered` files when run against any station, not only pyforge-marshal.
- **CAP-111 — The declared Python floor equals the tested floor** ← spec-fleet-consistency-standard CAP-5 (shipped 2026-09-09)
  - **intent:** A package's `requires-python` states what is actually exercised, not an aspiration nothing runs.
  - **success:** All ten packages declare `>=3.14`, matching `pixi.toml`'s `python = ">=3.14.7,3.14.*"` and every env-scoped `3.14.*` pin; no package claims support for an interpreter no environment in this repo installs.
- **CAP-112 — Governance docs cannot go stale silently** ← spec-fleet-consistency-standard CAP-6 (shipped 2026-09-09)
  - **intent:** When a skill is renamed, a script retired or a path moved, the governance documents that reference it fail a check instead of quietly misleading readers for months.
  - **success:** A detector resolves every `bmad-*` skill name, script path and file reference in `EXEMPLAR-STANDARD.md`, `AGENTS.md`, `CLAUDE.md` and `docs/reference/test-charter.md`, and exits non-zero naming each reference that no longer resolves; it is discovered by `scripts/detectors.py` and has its own pixi task; run against the pre-CAP-1 standard it reports all seven of this session's staleness findings.
- **CAP-113 — from spec-fleet-status-supervisor-fallback** ← spec-fleet-status-supervisor-fallback CAP-1 (shipped 2026-09-16)
  - **intent:** When `supervisor_alive is False`, `derive_home_state`'s caller consults a
  - **success:** Reproducing the 2026-08-11 scenario (a run resumed with no supervisor
- **CAP-114 — from spec-fleet-status-supervisor-fallback** ← spec-fleet-status-supervisor-fallback CAP-2 (shipped 2026-09-16)
  - **intent:** The two failure shapes (sidecar-dead-engine-alive vs. sidecar-dead-engine-dead)
  - **success:** An operator or an automated `fleet-picture` consumer can tell the two cases
- **CAP-115 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-1 (shipped 2026-09-16)
  - **intent:** Merge `epics-genesis-installer.md`'s content into one combined
  - **success:** Single `epics.md` file; `epics-genesis-installer.md` archived
- **CAP-116 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-2 (shipped 2026-09-16)
  - **intent:** Produce one contiguous functional-requirement numbering space via
  - **success:** Every FR in the regenerated PRD uses the dashed `FR-N` form,
- **CAP-117 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-3 (shipped 2026-09-16)
  - **intent:** Decide what happens to each installer-only namespace —
  - **success:** `grep` for the old bare forms across live planning-artifacts
- **CAP-118 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-4 (shipped 2026-09-16)
  - **intent:** Decide the CLI-framework contradiction instead of carrying it
  - **success:** The regenerated architecture states which framework the unified
- **CAP-119 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-5 (shipped 2026-09-16)
  - **intent:** Resolve the `init`/`check` verb collisions between Marshal's
  - **success:** The regenerated PRD names one verb surface — either one verb
- **CAP-120 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-6 (shipped 2026-09-16)
  - **intent:** Remove every "Satellite: Genesis Installer PRD/Architecture"
  - **success:** `grep -i "genesis.installer"` across the regenerated
- **CAP-121 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-7 (shipped 2026-09-16)
  - **intent:** Update the dashboard so the build-campaign section shows exactly
  - **success:** `pyforge.doctor.sources.fleet_scan`'s `IMPL_CAMPAIGN` has one marshal
- **CAP-122 — from spec-genesis-installer-name-retirement** ← spec-genesis-installer-name-retirement CAP-8 (shipped 2026-09-16)
  - **intent:** Preserve already-landed story identity through the rewrite —
  - **success:** Every story key with `status=done` before the rewrite has the
- **CAP-123 — from spec-horizontal-run-concurrency** ← spec-horizontal-run-concurrency CAP-1 (shipped 2026-09-16)
  - **intent:** An operator who requests `scm.max_parallel > 1` is told the request is inert,
  - **success:** Setting `max_parallel > 1` in a project's policy produces a registered
- **CAP-124 — from spec-horizontal-run-concurrency** ← spec-horizontal-run-concurrency CAP-2 (shipped 2026-09-16)
  - **intent:** The `bmad_loop` parallel-fan-out gap is tracked in the same upstream-contribution
  - **success:** `upstream-register.json` carries an entry for this gap (id, gap description,
- **CAP-125 — from spec-horizontal-run-concurrency** ← spec-horizontal-run-concurrency CAP-3 (shipped 2026-09-16)
  - **intent:** Marshal's own readiness for N-stories-in-flight — worktree isolation, the shared
  - **success:** A written readiness assessment exists, naming what already holds (e.g.
- **CAP-126 — from spec-landing-evidence-grammar** ← spec-landing-evidence-grammar CAP-1 (shipped 2026-09-09)
  - **intent:** ONE shared grammar of landing-evidence shapes — merge-subject templates,
  - **success:** The grammar recognizes, as written (or via the one-time reviewed allowlist of the
- **CAP-127 — from spec-landing-evidence-grammar** ← spec-landing-evidence-grammar CAP-2 (shipped 2026-09-09)
  - **intent:** Doctor-side adoption — `story-status`'s evidence routes (`sources/marshal.py:
  - **success:** On the live repo, the three standing `story-status` false positives (marshal 8-2,
- **CAP-128 — from spec-landing-evidence-grammar** ← spec-landing-evidence-grammar CAP-3 (shipped 2026-09-09)
  - **intent:** Marshal-side adoption — the promotion classifiers (`core/promotion.py:93-107`),
  - **success:** MRS-STATUS-010's UNCONFIRMED pile shrinks from 26 to only genuinely-unlanded
- **CAP-129 — from spec-landing-evidence-grammar** ← spec-landing-evidence-grammar CAP-4 (shipped 2026-09-09)
  - **intent:** Story 20.9's own doctor-side adoption of the grammar was incomplete in two ways,
  - **success:** All 25 standing false positives (doctor 6 stories, marshal 10, mason 7, steward 2
- **CAP-130 — from spec-library-catalog-manifest-sync** ← spec-library-catalog-manifest-sync CAP-1 (shipped 2026-09-12)
  - **intent:** Root `pixi.toml` and `docs/reference/library-llms-full.md` document the seven
  - **success:** `pixi run -e local-recipes llms-full-check` exits 0; each of the seven appears
- **CAP-131 — from spec-library-catalog-manifest-sync** ← spec-library-catalog-manifest-sync CAP-2 (shipped 2026-09-12)
  - **intent:** `scripts/llms_full_check.py`'s dependency walk also covers every
  - **success:** A synthetic station-manifest entry that is not mirrored in root `pixi.toml` or
- **CAP-132 — fleet-wide staleness detection** ← spec-loop-home-fleet-refresh CAP-1
  - **intent:** For every discovered loop-home (derived from the filesystem/`marshal homes`
  - **success:** run against today's fleet state (all homes pinned 227 commits back) and every
- **CAP-133 — automated fast-forward and push, with a clean-worktree safety check** ← spec-loop-home-fleet-refresh CAP-2
  - **intent:** For each stale home whose root checkout passes the safety checks (working tree
  - **success:** run against 9 clean-but-stale homes and all 9 end fast-forwarded and pushed,
- **CAP-134 — policy re-render as a checked step of the same refresh** ← spec-loop-home-fleet-refresh CAP-3
  - **intent:** After a home's fast-forward (or when CAP-1 flags its policy file
  - **success:** delete a home's `policy.toml` and run the refresh: the file is back and
- **CAP-135 — Re-preflight when the refuse predicate can change** ← spec-marshal-drain-self-resolution CAP-1 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-136 — Missing-spec escalates; never idle-with-backlog** ← spec-marshal-drain-self-resolution CAP-2 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-137 — Mechanical land-conflict union + local-clean when DIRTY** ← spec-marshal-drain-self-resolution CAP-3 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-138 — Push the dispatch branch before verify can strand it** ← spec-marshal-drain-self-resolution CAP-4 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-139 — Verify blast radius (`pre-existing-gate`)** ← spec-marshal-drain-self-resolution CAP-5 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-140 — Terminal overlay + stranded-work signal** ← spec-marshal-drain-self-resolution CAP-6 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-141 — Supervisor finalizes when the harness cannot run shell** ← spec-marshal-drain-self-resolution CAP-7 (shipped 2026-09-09)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-142 — the GitHub PR-merge pattern is scoped to `project_slug`** ← spec-marshal-land-cross-project-story-key-collision CAP-1 (shipped 2026-09-09)
  - **intent:** `extract_story_key_from_github_merge_subject`'s branch-segment
  - **success:** `merged_story_keys(subjects_from_main, template, 'mason')`
- **CAP-143 — from spec-marshal-land-merge-subject** ← spec-marshal-land-merge-subject CAP-1 (shipped 2026-09-16)
  - **intent:** `marshal land` renders the same templated merge subject `deploy land-story` already does (`identity.render_merge_subject(story_key, template)`, AD-24) and applies it to the GitHub merge, instead of leaving GitHub to auto-generate one.
  - **success:** `marshal_native_merged_keys(subjects, template, project_slug)`, given a real subject string from a `marshal land`-driven merge, classifies it as native — the same outcome it already produces for a `deploy land-story` merge.
- **CAP-144 — `** ← spec-marshal-launch-environment-integrity CAP-1 (shipped 2026-09-11)
  - **intent:** Reuse `cli/dispatch.py`'s `station_in_flight_conflict` check (a narrowed call,
  - **success:** A fixture reproduces the exact 2026-09-10 race (two spin calls six seconds
- **CAP-145 — A** ← spec-marshal-launch-environment-integrity CAP-2 (shipped 2026-09-11)
  - **intent:** The supervisor's own poll loop commits a local-only `wip: <story>
  - **success:** A fixture simulating a mid-session crash after the checkpoint fires asserts the
- **CAP-146 — `** ← spec-marshal-launch-environment-integrity CAP-3 (shipped 2026-09-11)
  - **intent:** A blocked story whose last recorded verdict shows zero git progress and zero
  - **success:** A fixture reproduces one of each (a crashed-before-any-progress run, a real
- **CAP-147 — T** ← spec-marshal-launch-environment-integrity CAP-4 (shipped 2026-09-11)
  - **intent:** A dedicated fixture pins `fleet_picture.py`'s `main()` ATTENTION-block branch
  - **success:** A station with `dispatch_phase` set and a `refused` verdict produces the
- **CAP-148 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-1 (shipped 2026-09-09)
  - **intent:** A **wave scheduler** on `factory drain` / fleet-supervisor ticks:
  - **success:** With `max_parallel=2` and two ready stories whose surfaces are
- **CAP-149 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-2 (shipped 2026-09-09)
  - **intent:** **Narrow `station_in_flight_conflict()`** (22.5 refinement): refuse
  - **success:** Story A with git-fact LIVE blocks story B only when B depends on
- **CAP-150 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-3 (shipped 2026-09-09)
  - **intent:** **`dispatch-wave` journal observability**: each wave records wave
  - **success:** A two-member wave produces one journal intent with both keys;
- **CAP-151 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-4 (shipped 2026-09-09)
  - **intent:** **Explicit cap, default serial:** `dispatch.max_parallel` in
  - **success:** Absent policy key and flag → serial. Policy `max_parallel=3`
- **CAP-152 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-5 (shipped 2026-09-09)
  - **intent:** **Compose with 28.12, do not duplicate:** ready-set and
  - **success:** Ready-set computation is imported/shared with 28.12 tests; no
- **CAP-153 — from spec-marshal-parallel-dispatch-fanout** ← spec-marshal-parallel-dispatch-fanout CAP-6 (shipped 2026-09-09)
  - **intent:** Factory fan-out gets its **own `dispatch.max_parallel` policy key**, resolved
  - **success:** A station declaring `dispatch.max_parallel = N` forms waves of up to N with no
- **CAP-154 — from spec-marshal-run-watch** ← spec-marshal-run-watch CAP-1
  - **intent:** An operator (or any caller of marshal's CLI) can run `marshal watch` against one
  - **success:** `marshal watch --project <slug> --run <run_id>` (bmad-loop pattern) and `marshal
- **CAP-155 — from spec-marshal-run-watch** ← spec-marshal-run-watch CAP-2
  - **intent:** `marshal watch` never conflates a live `bmad-loop` run's per-story ground truth
  - **success:** A test fixture where `marshal status --project <slug>`'s `dispatch_*` fields
- **CAP-156 — from spec-marshal-run-watch** ← spec-marshal-run-watch CAP-3
  - **intent:** `marshal watch`'s report is reachable over `POST /stations/marshal/mcp` as a
  - **success:** A new `@server.tool(...)`-registered tool in `django_marshal_portal/mcp_asgi.py`
- **CAP-157 — from spec-marshal-run-watch** ← spec-marshal-run-watch CAP-4
  - **intent:** The `bmad-agent-marshal` persona can offer "watch a run" as a named menu action
  - **success:** A menu entry exists in the persona's resolved `agent.menu` that, when selected,
- **CAP-158 — from spec-marshal-run-watch** ← spec-marshal-run-watch CAP-5
  - **intent:** The report CAP-1 produces is viewable in the `django-marshal` browser portal,
  - **success:** A new view + URL route in `django_marshal_portal` renders CAP-1's report for a
- **CAP-159 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-1
  - **intent:** An operator (or a fleet driver acting for one) can launch exactly one story
  - **success:** Dispatching a backlog story provisions a fresh isolated worktree, launches
- **CAP-160 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-2
  - **intent:** The driver judges a dispatched session's completion or failure from git facts
  - **success:** Two motivating traps are regression-pinned: (a) the driver awaiting a
- **CAP-161 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-3
  - **intent:** Verification is the product: before any landing, the driver itself runs the
  - **success:** A story whose session self-reports shipped but whose gates fail or whose
- **CAP-162 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-4
  - **intent:** A verified story lands through the existing Epic 4 machinery — `marshal
  - **success:** A dispatch-landed story is classified marshal-native by
- **CAP-163 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-5
  - **intent:** One story in flight per station, enforced: the driver refuses a second
  - **success:** A second dispatch to a busy station is refused naming the in-flight story;
- **CAP-164 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-6
  - **intent:** The dispatched run survives its operator: detached-by-default (AD-22
  - **success:** Killing the terminal that issued the dispatch leaves the session running; a
- **CAP-165 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-8
  - **intent:** The session-harness layer is adapter-plural and profile-driven: an ordered
  - **success:** With cursor unauthenticated and claude authenticated, a dispatch launches
- **CAP-166 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-7
  - **intent:** Fleet-wide drain across all eight pyforge stations is a marshal-orchestrated
  - **success:** An operator runs one documented command (provisional: `marshal factory
- **CAP-167 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-9
  - **intent:** CAP-2's `branch_merged` git fact is never true on ancestry alone.
  - **success:** A dispatch's `branch_merged` fact reads `false` for as long as
- **CAP-168 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-10
  - **intent:** Station-scoped and sequence-scoped dispatch, both handed as an override to
  - **success:** `--station` scopes one drain cycle to that station's next backlog story
- **CAP-169 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-11
  - **intent:** A story whose spec is `status: done` must not enter another
  - **success:** Replaying the 41.2 / 13.2 fixtures (spec already `done`,
- **CAP-170 — from spec-marshal-single-story-dispatch** ← spec-marshal-single-story-dispatch CAP-12
  - **intent:** CAP-3's bound verify command is a floor, not a ceiling: it
  - **success:** A story whose diff touches only its own station's package
- **CAP-171 — harness_run_id recovers via filesystem discovery** ← spec-marshal-status-harness-run-id-poisoning CAP-1 (shipped 2026-09-09)
  - **intent:** A status read for a run whose journal-poll timed out (`harness_run_id: null`)
  - **success:** Given a run whose journal entry has `harness_run_id: null` but whose
- **CAP-172 — `MRS-STATUS-002` keeps firing correctly for genuinely unrecoverable cases** ← spec-marshal-status-harness-run-id-poisoning CAP-2 (shipped 2026-09-09)
  - **intent:** A run whose directory truly cannot be found or read still reports `unknown`
  - **success:** Given a run with no discoverable `.bmad-loop/runs/` directory at all (or an
- **CAP-173 — from spec-marshal-templated-merge-subject-cross-project-collision** ← spec-marshal-templated-merge-subject-cross-project-collision CAP-1 (shipped 2026-09-11)
  - **intent:** A templated-form merge subject is trusted as `project_slug`'s own merged key
  - **success:** `merged_story_keys(subjects, template, 'pyforge-doctor', known_keys=...)` against
- **CAP-174 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-1
  - **intent:** A declared context pipeline: a `[context]` block in `EffectivePolicy`,
  - **success:** Rendered output carries the block from one composition site; a run on
- **CAP-175 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-2
  - **intent:** Wire compression at the harness seam: when policy enables it, sessions
  - **success:** The launched command is demonstrably wrapped; a compressed artifact is
- **CAP-176 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-3
  - **intent:** Output-compression seeding: Genesis deploys the caveman skill per loop home
  - **success:** `marshal seed check` verifies deployment; a landed story's verdict and
- **CAP-177 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-4
  - **intent:** Structure from the graph: loop-home provisioning builds/syncs the codegraph
  - **success:** Seed check proves the index present and fresh at admission; a session
- **CAP-178 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-5
  - **intent:** Incremental derived context: epic-context / continuity distills become
  - **success:** Unchanged sources yield zero recompute across two consecutive iterations; a
- **CAP-179 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-6
  - **intent:** Planning-graph retrieval: story routing retrieves the scoped planning
  - **success:** An epic-path iteration completes within the epic-context token target with
- **CAP-180 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-7
  - **intent:** Savings telemetry: the supervisor journals per-story spend AND per-layer
  - **success:** Journal entries carry savings fields; status shows them while a run is
- **CAP-181 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-8
  - **intent:** A graduated compression ladder: as a story approaches its token ceiling the
  - **success:** A test proves ladder ordering — compression escalation strictly precedes
- **CAP-182 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-9
  - **intent:** A measured baseline: a pinned, re-runnable benchmark (same story, layers on
  - **success:** The benchmark artifact reproducibly emits the comparison; ceiling
- **CAP-183 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-10
  - **intent:** Index freshness is an admission signal: `marshal check` gains advisory
  - **success:** A stale index yields a named finding; the exit-code domain
- **CAP-184 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-11
  - **intent:** A declared model-cost catalog: policy carries a price table (per
  - **success:** Journals, `marshal status`, and the benchmark artifact show dollar
- **CAP-185 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-12
  - **intent:** Difficulty tiers route across providers and pools: the `model_tier_map`
  - **success:** A declared difficulty demonstrably launches different provider/model pairs
- **CAP-186 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-13
  - **intent:** Graph-node staleness flag: `compile_graph` (Scribe's own compile-step,
  - **success:** A node whose source changed since compile with no declared supersession is
- **CAP-187 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-14
  - **intent:** `factory drain` (no caller-supplied `--stories`) derives dispatch order
  - **success:** A station whose backlog has a cross-epic dependency (verified:
- **CAP-188 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-15
  - **intent:** A dispatch ended by an external stop (SIGTERM outside marshal's own
  - **success:** An externally-stopped story is not journaled `MRS-DRAIN-005 failed`; it
- **CAP-189 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-16
  - **intent:** `policy_surface` resolution (feeding AD-27's existing narrow-only
  - **success:** A story touching only files under its own station's package tree and the
- **CAP-190 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-17
  - **intent:** A policy-declared, per-station scope-violation enforcement mode with three
  - **success:** A station with no mode declared runs `warn` (visible, non-blocking) — the
- **CAP-191 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-18
  - **intent:** One publisher: marshal publishes bmad-loop/dispatch run state *and* CAP-7's
  - **success:** marshal imports `django_pyforge` in exactly one publisher module (today it
- **CAP-192 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-19
  - **intent:** One substrate, many harnesses (the session-path fold, primary — the
  - **success:** A bare clone plus one bootstrap command reaches the same substrate
- **CAP-193 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-20
  - **intent:** Silent saves — a repo default that no-ops honestly.
  - **success:** A fresh loop home with zero station config journals the
- **CAP-194 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-21
  - **intent:** Marshal is the execution front door. The docs rule (AGENTS.md /
  - **success:** The front-door rule is written where an agent actually reads it;
- **CAP-195 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-22
  - **intent:** The session path — dispatch measured, interactive documented.
  - **success:** The interactive path is one documented invocation, not a
- **CAP-196 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-23
  - **intent:** Per-layer benchmark legs with cache-hit rates.
  - **success:** A named story runs one leg per layer; each artifact reports
- **CAP-197 — from spec-marshal-token-economy** ← spec-marshal-token-economy CAP-24
  - **intent:** The multi-harness matrix tells the truth, per currency. Correct
  - **success:** The matrix records each harness × layer × binding currency;
- **CAP-198 — Verify-refusal terminalization (supervisor)** ← spec-marshal-verify-fail-terminalization CAP-1 (shipped 2026-09-09)
  - **intent:** When `session_alive == false`, independent verify outcome is
  - **success:** Fixture: dead session + journaled verify refuse + WIP commit →
- **CAP-199 — Transient auto-redispatch (fleet drain, compose with hotfix)** ← spec-marshal-verify-fail-terminalization CAP-2 (shipped 2026-09-09)
  - **intent:** After CAP-1, `classify_dispatch_block` (existing hotfix) treats
  - **success:** Integration test or documented cycle: failed+preserve run →
- **CAP-200 — Observability** ← spec-marshal-verify-fail-terminalization CAP-3 (shipped 2026-09-09)
  - **intent:** `marshal status` / completion payload names
  - **success:** Journal observation entry or completion payload includes failed
- **CAP-201 — worktree-aware `bmad-switch`** ← spec-multi-loop-isolation CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-202 — `bmad-loop-worktree` provisioner** ← spec-multi-loop-isolation CAP-2 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-203 — isolation verification** ← spec-multi-loop-isolation CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-204 — from spec-one-front-door** ← spec-one-front-door CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-205 — from spec-one-front-door** ← spec-one-front-door CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-206 — from spec-one-front-door** ← spec-one-front-door CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-207 — from spec-one-front-door** ← spec-one-front-door CAP-5 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-208 — from spec-pr-lifecycle** ← spec-pr-lifecycle CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-209 — from spec-pr-lifecycle** ← spec-pr-lifecycle CAP-2 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-210 — from spec-pr-lifecycle** ← spec-pr-lifecycle CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-211 — from spec-pr-lifecycle** ← spec-pr-lifecycle CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-212 — from spec-quick-dev-reconciliation** ← spec-quick-dev-reconciliation CAP-1 (shipped 2026-09-09)
  - **intent:** Something observes git (repository fact) plus existing spec/story-identity
  - **success:** Given a story merged to the integration branch with no corresponding
- **CAP-213 — from spec-quick-dev-reconciliation** ← spec-quick-dev-reconciliation CAP-2 (shipped 2026-09-09)
  - **intent:** A detected non-loop completion is folded into the tracked ledger -- the
  - **success:** `marshal status` / the fleet dashboard shows a quick-dev'd story as `done`
- **CAP-214 — from spec-quick-dev-reconciliation** ← spec-quick-dev-reconciliation CAP-3 (shipped 2026-09-09)
  - **intent:** A quick-dev'd story's spec receives the same durability guarantee Story 4.1
  - **success:** A quick-dev'd story's spec, once its story is detected as done, is
- **CAP-215 — from spec-quick-dev-reconciliation** ← spec-quick-dev-reconciliation CAP-4 (shipped 2026-09-09)
  - **intent:** An operator can hand-pick any backlog story for `bmad-quick-dev` while that
  - **success:** Reconciling a quick-dev completion around a live, unrelated loop run neither
- **CAP-216 — surface-manifest convention** ← spec-regenerable-factory CAP-1 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-217 — backfill waves** ← spec-regenerable-factory CAP-2 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-218 — repo-wide surface checker** ← spec-regenerable-factory CAP-3 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-219 — regeneration drill** ← spec-regenerable-factory CAP-4 (shipped 2026-09-16)
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-220 — from spec-risk-tiered-review-depth** ← spec-risk-tiered-review-depth CAP-1
  - **intent:** A story is classified into a review weight before review runs, mechanically,
  - **success:** Given a story's declaration and its observed diff, the classification
- **CAP-221 — from spec-risk-tiered-review-depth** ← spec-risk-tiered-review-depth CAP-2
  - **intent:** Review depth/cost varies by weight without ever skipping the independent
  - **success:** A test proves the reviewer runs on every story regardless of weight, and that
- **CAP-222 — from spec-risk-tiered-review-depth** ← spec-risk-tiered-review-depth CAP-3
  - **intent:** `deferred-work-check`'s full-capture guarantee holds at every tier -- a
  - **success:** A regression test reproduces the `DW-AD23-3` shape (a follow-up recommended
- **CAP-223 — from spec-risk-tiered-review-depth** ← spec-risk-tiered-review-depth CAP-4
  - **intent:** The tier a story's review ran at, and why, is visible in the same
  - **success:** The envelope for any evaluated story carries its review-weight tier and the
- **CAP-224 — from spec-run-state-one-publisher** ← spec-run-state-one-publisher CAP-1
  - **intent:** The host holds a run it does not own — the supervisor store accepts, keeps
  - **success:** An externally published run stays `running` across its heartbeats and is
- **CAP-225 — from spec-run-state-one-publisher** ← spec-run-state-one-publisher CAP-2
  - **intent:** A published external run is attributable to a verified subject — the
  - **success:** A publish without a verifiable assertion is refused and leaves no row; a
- **CAP-226 — from spec-run-state-one-publisher** ← spec-run-state-one-publisher CAP-3
  - **intent:** The deployed proof is exercised and recorded — CAP-17's success criterion runs
  - **success:** The mechanism tier gates in `platform-ci-local --test` (publish, exit, re-query
- **CAP-227 — from spec-run-state-one-publisher** ← spec-run-state-one-publisher CAP-4
  - **intent:** No run-state read from a home directory remains in the fleet — every read of
  - **success:** A kind-aware guard over non-test code matches the `.bmad-loops` literal and the
- **CAP-228 — from spec-run-state-one-publisher** ← spec-run-state-one-publisher CAP-5
  - **intent:** The operator's bearer reaches the publisher by reference, and marshal is a
  - **success:** `pyforge login` writes the bearer file with owner-only permissions and nothing
- **CAP-229 — promotion runs on landing, not on memory** ← spec-sprint-status-auto-promote CAP-1
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-230 — staleness is detectable on its own** ← spec-sprint-status-auto-promote CAP-2
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-231 — the check is real, never approximated** ← spec-sprint-status-auto-promote CAP-3
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-232 — never races the orchestrator** ← spec-sprint-status-auto-promote CAP-4
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-233 — promotion never writes the operator checkout** ← spec-sprint-status-auto-promote CAP-5
  - **intent:** (see absorbed Spec memlog)
  - **success:** (see absorbed Spec memlog)
- **CAP-234 — from spec-sprint-status-promotion-regression-guard** ← spec-sprint-status-promotion-regression-guard CAP-1 (shipped 2026-09-16)
  - **intent:** An operator promoting Tier-3 status into the tracked ledger can trust that any
  - **success:** Given a tracked-ledger key whose status is `done` and whose Tier-3 twin holds
- **CAP-235 — b** ← spec-surface-drift-reconciliation CAP-1 (shipped 2026-09-09)
  - **intent:** An operator settles one spec's baseline without accepting any other spec's pending drift.
  - **success:** `--write-baseline --spec NAME` merges only that spec's entry into the committed baseline and leaves every other entry byte-identical; an unknown spec name exits 2 with the known names listed; unscoped `--write-baseline` still works and states in its own help text that it accepts every other spec's pending drift.
- **CAP-236 — a** ← spec-surface-drift-reconciliation CAP-2 (shipped 2026-09-09)
  - **intent:** A memlog entry stops speaking for governed files it never mentions, so unrelated activity cannot launder pending drift.
  - **success:** With a spec's memlog moved, a drifted file **named** in that memlog clears while an **unnamed** one reports `[drift-presumed]`; appending an unrelated memlog entry no longer changes the verdict for an untouched governed file (the live 63 → 61 laundering no longer reproduces).
- **CAP-237 — t** ← spec-surface-drift-reconciliation CAP-3 (shipped 2026-09-09)
  - **intent:** An operator can act on the verdict because every finding is dispositioned rather than carried.
  - **success:** Each of the 24 `[no-baseline]` scoped-stamped; each of the 34 `[drift]` either genuinely reconciled through its spec or scoped-stamped with the reasoning recorded in that spec's memlog; both `[ungoverned]` files given a surface or allowlist entry; the one `[stale-allowlist]` pattern removed. Anything that cannot be honestly cleared is filed as deferred work with its reason, never suppressed.
- **CAP-238 — t** ← spec-surface-drift-reconciliation CAP-4 (shipped 2026-09-09)
  - **intent:** Neither fix can silently regress into the blanket behavior it replaces.
  - **success:** Both are mutation-tested **both ways** — removing `--spec` scoping re-reds the isolation test, and restoring the per-spec short-circuit re-reds the laundering test — and `spec-surface-check` exits 0 on `main`.
- **CAP-239 — t** ← spec-surface-drift-reconciliation CAP-7 (shipped 2026-09-09)
  - **intent:** bmad-loop names the governed paths it changed in the owning Spec's memlog as part of the story, so the spec-surface gate stops being a tax paid by whoever lands the work.
  - **success:** A loop-produced story that changes governed files leaves that Spec's `.memlog.md` naming each changed path before the story is marked complete; `spec-surface-check` is green on the loop's own station branch without a human editing a memlog; a story that changes NO governed file writes nothing (silence is not a finding); and the reconciliation is per-file naming under S-13.2's rule, never a blanket stamp — the loop must not be handed `--write-baseline`.
- **CAP-240 — t** ← spec-surface-drift-reconciliation CAP-6 (shipped 2026-09-09)
  - **intent:** The 994 `[drift-presumed]` entries CAP-2 made visible are dispositioned, so the informational channel stays small enough to read and a new entry means something.
  - **success:** Every presumed entry is traced to the commit that last moved it and partitioned — `added` (baseline lag) vs `changed` (the per-file question) — with each cluster judged against its Spec's own capabilities and the judgment recorded in that Spec's memlog before any stamp; anything moved by a story that is **not** `done`, or landing outside a contracted capability, is reported rather than stamped; the four Specs are then scoped-stamped individually and `spec-surface-check` reports **0 findings and 0 `[drift-presumed]`**, with a before/after diff proving no gating `[drift]` was absorbed.
- **CAP-241 — a** ← spec-surface-drift-reconciliation CAP-5 (shipped 2026-09-09)
  - **intent:** A Spec that declares a `surface:` but has no `.memlog.md` stops being silently drift-blind — its contract hash is `""`, so the contract can never move and the "reconcile the spec" remedy the detector prints is unreachable.
  - **success:** A spec that governs ≥1 tracked file under the default `surface-drift: memlog` mode with no `.memlog.md` reports a **gating** `[drift-blind]` finding naming the spec, its governed count, and the path the memlog belongs at; a spec governing zero files, an `exempt` spec, and a `sentinel:` spec each report nothing (their contracts cannot go blind); the 7 live instances (396 governed files) are dispositioned by creating each memlog **and** scoped-stamping its baseline in the same change, verified by a before/after diff showing no `[drift]` moved to `[drift-presumed]`; mutation-tested both ways — removing the check re-greens a fixture whose memlog was deleted, restoring it re-reds.
- **CAP-242 — from spec-surface-overlap-tolerance** ← spec-surface-overlap-tolerance CAP-1
  - **intent:** A file governed by multiple specs is `drift-presumed`/`drift` only when
  - **success:** A synthetic fixture with two specs governing the same file, where one
- **CAP-243 — from spec-surface-overlap-tolerance** ← spec-surface-overlap-tolerance CAP-2
  - **intent:** A genuinely unreconciled change is still caught exactly as today — this
  - **success:** The existing `spec-surface-check` test suite's single-owner drift/
- **CAP-244 — a landing never re-dispatches the story it just landed** ← spec-pyforge-marshal CAP-244 (ready 2026-09-18)
  - **intent:** The fleet campaign supervisor treats the window between a dispatch session exiting and `dispatch_land_finalize` promoting the ledger as *still in flight*, so a story is never re-dispatched, never refuses itself, and never turns its own refusal into a campaign-ending block.
  - **success:** With a story whose session has exited but whose supervisor has not yet journaled `dispatch-completion`/`dispatch-land`, the next cycle reports that station `in-flight` (MRS-DISP-011-shaped), never `dispatched`; a story whose most recent run is a self-refusal of the already-merged kind classifies as **advance**, not `blocked`, so the campaign chains the next ready story; a drain over ≥2 serial stories completes with zero operator relaunches, proven on a fixture journal replaying the 2026-09-18 herald sequence (`…151925342Z-82ce96c8`: dispatched 15:19Z → landed 16:21Z → respawned 16:20:47Z → blocked, complete).
- **CAP-245 — a harness's own usage-wall wording is a transient outcome** ← spec-pyforge-marshal CAP-245 (ready 2026-09-18)
  - **intent:** A session that dies on a harness quota/usage wall is classified `quota_exceeded` (transient) from the harness's *current* wording, so the fleet planner retries or re-routes it instead of recording a terminal block.
  - **success:** `classify_session_log` returns `QUOTA_EXCEEDED` for Cursor's live text (`ActionRequiredError: Increase limits for faster responses You're out of usage. Switch to Auto, or ask your admin to increase your limit`) and for the Claude Code weekly/monthly limit text already catalogued; the marker table is per-harness and read from one place; `classify_dispatch_block` on the real `…132400673Z-194af3a0` session log with zero changed paths returns `TRANSIENT`; mutation-tested — removing the new marker re-terminalises the fixture.
- **CAP-246 — `--harness` outranks a dead tier-map harness** ← spec-pyforge-marshal CAP-246 (ready 2026-09-18)
  - **intent:** An explicit `--harness` invocation flag is the operator's word and beats the tier map's inline-table harness for that dispatch, without editing policy; a tier-map harness the flag excludes contributes nothing to the walk.
  - **success:** With a station policy naming `{ harness = "cursor", … }` for dev and `--harness claude`, `resolve_tier_harness` leads the walk with `claude` and the launch journal records `harness_profile: claude`; the model override is resolved for the harness actually chosen (the harness's own default when the tier map names no model for it), never a foreign model id (fails-safe CAP-1 of spec-cursor-native-tier-map preserved); without the flag, today's tier-map-leads behaviour is byte-identical. Proven against herald's pre-#1458 policy as a fixture.
- **CAP-247 — landing evidence carries the station in every shape** ← spec-pyforge-marshal CAP-247 (ready 2026-09-18)
  - **intent:** No commit subject shape can mark a story merged for a station it does not name: the AD-24 templated shape renders and parses with the station slug, and the un-scoped `Story N.M:` direct-commit shape is corroborated by branch or station evidence before it counts.
  - **success:** The repo default `merge_subject_template` becomes `Merge {slug}/{key} into main` (rendered `Merge pyforge-herald/23-1 into main`, exactly herald's #1458 form) and `parse_templated_merge_subject` refuses a subject whose slug segment is another station's; `merged_story_keys` for `pyforge-marshal` against today's origin/main no longer contains 48.2/48.4 (steward's `Story 48.2:` / `Story 48.4:` subjects) nor 23.1..23.6 for herald (atlas's `Merge 23-N into main`); every shipped station's own already-landed keys still classify (regression fixture over the eight ledgers' `done` rows vs. `git log`); the repo's live `Merge {key} into main` history is grandfathered through the SHA/recovery allowlist, never re-attributed.
- **CAP-248 — the promoter reads a spec through its banner** ← spec-pyforge-marshal CAP-248 (ready 2026-09-18)
  - **intent:** A tracked story spec whose frontmatter is preceded by an HTML comment banner is still a valid, already-promoted spec; the promotion scan never overwrites a tracked copy with a Tier-3 twin because of a banner.
  - **success:** `is_valid_spec_text` (and `parse_declared_surface`, which shares the "must start with `---`" assumption) accept a leading `<!-- … -->` block before the frontmatter; `_already_promoted_keys` counts herald's pre-#1460 `spec-1-4` as promoted; a fixture with a banner-topped tracked spec and a differing Tier-3 twin produces an empty `to_promote`; the 45 files #1460 moved are unaffected either way.
- **CAP-249 — verification sees the merge result** ← spec-pyforge-marshal CAP-249 (ready 2026-09-19)
  - **intent:** A story lands only after its verification ran against the tree `main` will actually contain: a baseline that predates a sibling's landing on overlapping files is re-verified on the merged tree before the PR merges, instead of being refused at land (MRS-DISP-038, PR left open) or auto-merged into a runtime break.
  - **success:** On a fixture branch whose baseline predates a sibling landing on the same module (the 50.4 / doctor 27.5 pair — `bare_merge.py`'s 2-arg call against the new 3-arg signature, hand-composed as `1a5895317f`), `dispatch land` materialises `git merge-tree --write-tree origin/main <head>`, runs the station's own `verify_commands` against that tree, and refuses with a named finding when it is red; a conflict-free green merge lands with no operator action; a branch whose baseline already equals `origin/main` verifies exactly once (byte-identical to today); mutation-tested — removing the merged-tree run lets the fixture land green.
- **CAP-250 — the landing record follows the session's write, not the primary's directory** ← spec-pyforge-marshal CAP-250 (ready 2026-09-19)
  - **intent:** Whatever the dispatched session wrote into its worktree's Tier-3 twin — Review Triage Log, Auto Run Result, `followup_review_recommended`, `deferred:` — is promoted into the tracked spec by finalize, and a land refused after the PR was opened still journals the PR it opened.
  - **success:** On a fixture where the session wrote its record to `<worktree>/_bmad-output/projects/<slug>/implementation-artifacts/spec-<key>-*.md` (tracked spec as `context:`) and flipped only `status:` on the tracked copy (50.4's shape, promoted by hand in #1488), `dispatch_land_finalize` promotes the twin so the tracked spec carries `## Auto Run Result` and every `deferred:` item reaches `deferred_work_intake.py` — the worktree's `implementation-artifacts/` is a discovery source beside the primary's, read before teardown; the `dispatch-land` journal projection for a refusal after PR open carries `pr_number` and `marshal_native` (today's REFUSED result drops both); the primary-directory promotion path is byte-identical.
- **CAP-251 — the campaign reads the ledger it just promoted** ← spec-pyforge-marshal CAP-251 (ready 2026-09-19)
  - **intent:** After finalize promotes the tracked ledger onto `origin/main`, the next campaign cycle reads that promoted state without an operator `git pull`.
  - **success:** On a fixture replaying the herald 23.x sequence (ledger promoted on `origin/main`, primary checkout one commit behind), the cycle after `dispatch-land` reports the story `done` and chains the next ready story with zero operator commands; the primary checkout is fast-forwarded only when it is a clean `main` (`marshal refresh`'s contract) — a dirty or non-`main` checkout is refused by name and journaled, never moved, and the campaign still reads the promoted state from `origin/main`; `_promote_sprint_ledger` keeps a single writer onto the remote tip.
- **CAP-252 — a blocked or hollow outcome never lands** ← spec-pyforge-marshal CAP-252 (ready 2026-09-19; widened 2026-09-19 after the 51.3 hollow landing)
  - **intent:** A session that ends `blocked` — intent gap found, branch reverted to baseline, `status: blocked` written — or hollow — no changed path outside the story's own tracked spec, the shape a harness-terminated session leaves — produces no PR, no `done` promotion, and a journal fact carrying the reason, so the ledger tells the truth and the story is re-driven or re-minted deliberately.
  - **success:** On a fixture of doctor 27.3 (empty diff against baseline plus `status: blocked` in the worktree spec; PR #1476 landed it and promoted `27-3 → done`) and a fixture of marshal 51.3 (branch diff = the tracked spec's frontmatter flip only; session log ending `Background tasks still running after 600s; terminating`; PR #1501 landed it and promoted `51-3 → done`), the supervisor's finalize sequence stops before verify and land, journals `dispatch-blocked` with the reason, the campaign records a station block (not an advance) — the harness-ceiling wording classified `transient`, re-dispatchable — and the tracked ledger row never reads `done`; the progress predicate ahead of land is scope-aware (changed paths ∩ the story's Surface ≠ ∅, or at minimum any path outside `planning-artifacts/specs/spec-<key>*.md`), never "HEAD moved"; the pre-launch `parse_spec_status` guard treats `blocked` as not relaunchable without an operator decision; an implementation with changed paths lands exactly as today.
- **CAP-253 — MRS-DISP-043 speaks for an uncatalogued model** ← spec-pyforge-marshal CAP-253 (ready 2026-09-19)
  - **intent:** The fails-safe guard fires when a tier-mapped model is catalogued under no provider at all, not only when it is catalogued under a different provider — with a predicate that keeps the chosen harness's own default and alias ids silent.
  - **success:** A fixture tier map naming a model id that no provider declares and that is not the chosen harness's own default/alias set raises MRS-DISP-043 before launch; the same launch with `sonnet` on claude (uncatalogued by design per `provider_declaring_model`'s own docstring) is byte-identical — no finding; the cross-provider case is unchanged; mutation-tested — removing the uncatalogued branch silences the fixture. Closes DW-FU-50-3.
- **CAP-254 — `marshal watch` follows the engine that is actually driving the station** ← spec-pyforge-marshal CAP-254 (ready 2026-09-19)
  - **intent:** The watch resolves a station's current run from the engine whose journal moved last, so a station driven by `factory dispatch` reports the dispatch run rather than a bmad-loop row paused in August.
  - **success:** On a fixture where `bmad-loop list` reports a `paused` row from 2026-08 and `dispatch-runs/` holds a run journaled today, `marshal watch <station>` reports the dispatch run (harness, key, phase, last journal fact); with no dispatch run the loop row is chosen exactly as today; a station with neither reports idle; the choice is one pure function over both facts, mutation-tested.
- **CAP-255 — landing evidence is intent-scoped, not just station-scoped** ← spec-pyforge-marshal CAP-255 (ready 2026-09-19)
  - **intent:** A branch that merely mentions a story key in a station-prefixed name is not that story's landing branch. For the dispatch consumers (the supervisor's `story_merged_on_main`, dispatch_land's already-landed check, finalize's promotion) a station-branch match reached through a GitHub PR-merge subject is corroborated by content, not name: it counts only when the key's tracked story spec on `origin/main` reads `status: done` — a mint, fallout or fix PR merges it `ready`/`backlog`, a landing merges the promoted twin (CAP-248/250). The retrospective scanners keep their breadth; live history is never re-attributed. (Refined 2026-09-19 night after run `…-0b70f736` returned blocked: name-based corroboration is unreachable through `_classify_merge_subject`, and an exact-match branch grammar would drop the only evidence for 83 of 347 marshal `done` rows.)
  - **success:** on the PR #1477 fixture (`doctor/27-4-mint`) 27.4 is absent from `promotion.corroborated_merged_story_keys` and present in `merged_story_keys`; every `done` row of the eight tracked ledgers with real landing evidence still classifies retrospectively (the CAP-247 fixture extended, the 347-key marshal sweep unchanged); a hollow landing whose spec is not `done` is not corroborated (consistent with CAP-252); `landing_evidence.LandingEvidenceMatch` exposes the branch-derived shape and `landing_evidence.py` stays a pure parser; the three dispatch consumers call the corroborated form and the four retrospective scanners (`cli/status.py`, `cli/deploy.py`, `cli/land.py`, doctor `sources/marshal.py`) are unchanged; `pyforge-core-test` and `pyforge-doctor-test` stay green (co-governed by spec-landing-evidence-grammar / spec-pyforge-core). DW-FU-50-4 is no longer claimed by this CAP.
- **CAP-256 — the banner-skip family is complete** ← spec-pyforge-marshal CAP-256 (ready 2026-09-19)
  - **intent:** Every marshal reader that skips a provenance banner tolerates leading whitespace or a BOM before `<!--`, and the one banner-blind sibling reachable through a promoted tracked spec skips it too, so no tracked spec is misread as unpromoted or as `declared_low_risk: false`.
  - **success:** `_skip_leading_banner` in `core/promotion.py` and `core/spec_surface.py` accept a banner preceded by blank lines, spaces or a BOM (DW-FU-50-6, severity high); `core/spec_low_risk.py::parse_declared_low_risk` reads `declared_low_risk: true` through a banner so `cli/gate.py::_gather_review_depth` resolves the declared depth (DW-FU-50-5); a spec with no frontmatter or an unclosed banner stays invalid; the 45 banner-below-frontmatter files parse identically; `spec_difficulty.py` and `dispatch_harness_done.py` are untouched (verified unreachable) — no new gate, no second parser.
- **CAP-257 — the watch's marshal-status probe is executable and proven against the real interpreter** ← spec-pyforge-marshal CAP-257 (ready 2026-09-20)
  - **intent:** `cli/watch.py`'s `marshal_home` probe invokes the marshal CLI by a module name this interpreter can execute (the console script's module, `pyforge.marshal.cli.main`, held in one module-level constant), so `_gather_station`'s dispatch-run detection (CAP-254 / Story 51.6) actually fires: a station with a live dispatch run is reported by its `dispatch_run_id`, phase and last journal fact, never as idle. (Found 2026-09-20 00:38Z: `marshal watch --fleet` read all eight stations idle while three dispatch sessions ran — `python -m pyforge.marshal` has no `__main__`, `ProcessError` → `None` on every call, and the probe's unit test asserted that wrong argv against a fake.)
  - **success:** on the fleet observed 2026-09-20 00:38Z `marshal watch --fleet` names all three live runs; a regression test runs `[sys.executable, "-m", <the constant>, "--help"]` through the `pyforge.core` process primitive and asserts exit 0; the fake-probe unit tests assert the argv against the same constant, never a literal; the probe stays advisory (`ProcessError` / non-JSON → `None`); no new subprocess implementation (spec-pyforge-core CAP-7 holds); `pyforge-marshal-test` green.
- **CAP-258 — a session that halts blocked with its verdict uncommitted is a blocked outcome, not an operator stop** ← spec-pyforge-marshal CAP-258 (ready 2026-09-20)
  - **intent:** when a dispatched session exits on its own and the worktree's *working tree* (not only `HEAD`) carries the tracked story spec at `status: blocked` with an Auto Run Result, the supervisor writes `dispatch-blocked` (reason: the spec's blocking condition), preserves the worktree and completes with verdict `blocked` — never `external-operator-stop` / `dispatch-finalize ok:false`; the uncommitted spec and any saved attempt patch are committed onto the dispatch branch so the record survives worktree teardown, and the primary's tracked twin is promoted so `fleet-picture` shows the block. (Found on doctor run `pyforge-doctor-20260919T233255320Z-8f2b958e`: CAP-252's detection reads committed state only; marshal 51.7's halt was caught only because that session committed the blocked spec first.)
  - **success:** replaying that run's final state (two wip commits with code, working tree = reverted code + blocked spec, session gone) yields `dispatch-blocked` + completion verdict `blocked` and a branch commit carrying the blocked spec; a session that dies with a clean working tree and no terminal spec status still reads `stopped_externally` (the classifier narrows, never widens); the committed-halt path is unchanged; the supervisor never trusts a self-report — it reads the spec file, `git status` and the process, nothing the session prints.
- **CAP-259 — a dispatch-only checkout still has fleet rows** ← spec-pyforge-marshal CAP-259 (ready 2026-09-20)
  - **intent:** `marshal status` (and so `marshal watch`, whose `marshal_home` probe reads it) reports a station whose Tier-3 under this checkout carries a dispatch run even when no `loop/<slug>` worktree exists here — the one-station-per-clone pattern MRS-DISP-041 prescribes — by giving it the Spec's own "home with no run yet" placeholder row (`has_run=False`) for the dispatch overlay to fill from the run journal, exactly as a loop-home row is filled. (Found 2026-09-20 00:47Z while proving CAP-257: the marshal and steward clones returned `homes: []` with their dispatch sessions live, because `run_status`'s fleet sweep is a git-worktree scan for `loop/` branches.)
  - **success:** from a clone with no loop homes and a live dispatch run, `marshal status --project <slug> --format json` names the run (`dispatch_run_id`, state `running`); a loop-home station is never duplicated by its own Tier-3 run; `--project` scopes a dispatch-only station like any other; discovery reads `cli/dispatch.py`'s own locators, never a second directory convention; a checkout with no `_bmad-output/projects/` yields no rows; the placeholder never engages `derive_home_state` or `journal_unreadable`.
- **CAP-260 — the watch reads the dispatch verdict in the supervisor's own vocabulary** ← spec-pyforge-marshal CAP-260 (ready 2026-09-20)
  - **intent:** `cli/watch.py`'s dispatch snapshot decides "finished" from `core/dispatch_completion.py`'s `DispatchSessionVerdict` — a run is finished only when its completion verdict is a member of that enum other than `LIVE`; `live`, absent, empty or unknown values read as the home's own state (`running` / `awaiting-operator` / …), never as finished; no second vocabulary of verdict strings exists in the watch or its tests. (Found 2026-09-20 01:25Z the moment CAP-257 made the probe return data: a two-minute-old run read *finished* because `marshal status` reports `dispatch_completion_verdict: live` and the snapshot's terminal test was "anything outside `{"", None, pending, in-progress}`"; `test_watch.py` asserted with `passed`/`pending`, values the supervisor never emits.)
  - **success:** a status row with state `running` and verdict `live` snapshots as status `running` / `finished: false`; `completed`, `failed` and `stopped_externally` snapshot finished; the watch's tests use only `DispatchSessionVerdict` members (a meta-test refuses any other verdict literal); on the live fleet the three running dispatches read `running`; `pyforge-marshal-test` green.
- **CAP-261 — the dispatch landing pays its own surface tax** ← spec-pyforge-marshal CAP-261 (ready 2026-09-20)
  - **intent:** CAP-239 extended from bmad-loop to `marshal factory dispatch`, both ends. (a) The dispatched session is told and gated the way a loop session is: the `harness_bmadbuild` prompt states the obligation (name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names; never `--write-baseline`; every `deferred:` entry cites a repo path in `location:`), and the S-13.7 guard (`python scripts/spec_surface_reconcile.py`) is part of the session's verification — appended at render like the loop's, derived never declared, with MRS-GATE-010 treating the derived guard as implicit so no tracked spec changes. (b) The landing reconciles from git facts as the safety net: before merging, `dispatch_land` runs the spec-surface verdict over the branch's changed governed paths and, for every Spec whose drift consists only of this branch's files, appends one event naming each path (story key, run id) on that Spec's memlog and on each co-governor the detector names, scoped-stamps exactly those Specs, commits onto the dispatch branch, journals `MRS-DISP-047` (warn: the session left N paths unreconciled; the landing named them), then merges; finalize runs `deferred_work_intake --fix` for the station and journals any refusal. Never a bare `--write-baseline`; never a stamp for a Spec whose drift includes files this branch did not change — that is foreign drift, the landing is refused naming those paths (`MRS-DISP-048`); a session that reconciled itself triggers nothing.
  - **success:** a dispatch of a story that changes governed files lands with `spec-surface` green on `main` and no memlog edited by a human; on the 2026-09-20 fixture (the changed paths of 26.1, 61.3, 51.11, 29.1, 61.4, 46.7) every path is named on the right Specs; a branch sharing a Spec with foreign drift is refused naming the foreign paths; the harness prompt carries the obligation verbatim; the guard runs in the session's verification and MRS-GATE-010 passes on every pre-authored spec unchanged; a deferral without `location:` is ingested or journaled; `pyforge-marshal-test` green; the loop path (CAP-239) byte-identical.
- **CAP-262 — the dispatched Claude session is launched with the instruction-file mode pinned** ← spec-pyforge-marshal CAP-262 (ready 2026-09-20)
  - **intent:** the claude harness profile's launch argv passes `--settings` with the `agents-md` mod's option inline (`{"pluginConfigs":{"agents-md@builtin":{"options":{"instructionFiles":"claude-md-and-agents-md"}}}}`), so a dispatched `claude -p` session loads nested `AGENTS.md` files (the atlas child) regardless of the operator's user settings; older Claude Code ignores an unknown plugin option and still reads `AGENTS.md` through `CLAUDE.md`'s import, so the pin is harmless below 2.1.277.
  - **success:** `render_dispatch_argv` for the claude profile yields `--settings` followed by JSON whose `pluginConfigs.agents-md@builtin.options.instructionFiles` is `claude-md-and-agents-md`; `{prompt}` still appears exactly once; the wire-wrapped launch keeps the same tokens; authcheck and model translation unchanged; `pyforge-marshal-test` green. Surface half: `spec-pyforge-scribe:CAP-29`.
- **CAP-263 — marshal's shell-outs name the Guild env** ← spec-pyforge-marshal CAP-263 (ready 2026-09-20)
  - **intent:** `cli/watch.py`'s bmad-loop list/status probes, `core/gate.py`'s `platform-ci-local` verify line and `adapters/scribe_cli.py`'s fallback bin dirs reach their commands through `-e pyforge-guild` (bmad-loop is marshal's own run-dep, already in the Guild), never `-e local-recipes` and never `.pixi/envs/local-recipes`; the watch's fake-port tests assert the Guild argv.
  - **success:** no `-e local-recipes` / `envs/local-recipes` string remains in `pyforge-marshal/src`; the watch, gate and scribe-CLI tests pass with the Guild argv; steward 63.6's meta-test lists no marshal offender; `pyforge-marshal-test` green.
- **CAP-264 — the dispatch supervisor entrypoint reaches the coverage floor** ← spec-pyforge-marshal CAP-264 (ready 2026-09-20)
  - **intent:** `dispatch_supervisor/__main__.py` (623 statements, 388 uncovered, 35% on 2026-09-20) is unit-covered to the station floor (80%) through ports-driven tests of its finalize / halt / land / completion sequences, and the per-module floor exception the 53.2 landing added to `coverage_thresholds.toml` is removed in the same story.
  - **success:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` reports the module ≥ 80% with no exception entry; the gate's OK line names no dated exception for marshal.
- **CAP-265 — a landing's ledger promotion repairs its own feed drift, never a human's job** ← spec-pyforge-marshal CAP-265 (ready 2026-09-24)
  - **intent:** `dispatch_land_finalize`'s promotion of the just-landed story into the tracked `sprint-status-ledger.yaml` retries with the Tier-3 feed's stale-but-safe keys repaired from the tracked twin (the same pull-forward `--repair-feed` already does, which is strictly safe — the twin is the authoritative record and the operation only ever moves a key toward `done`) whenever `sprint-ledger-sync`'s regression guard refuses solely because of keys *other than* the one being promoted; the feed catch-up lands in the SAME commit as the story it promotes, never a separate PR. The guard still refuses, and still needs a human, when the disagreement is about the story actually being promoted — that stays a genuine judgment call, not blind drift.
  - **success:** doctor 24.2 and 24.3 (PRs #1577/#1578 merged, spec `status: done`; PRs #1579/#1580 merged, spec `status: done`) are the reproduction fixture — replaying either landing's stale-feed shape (13 and 14 unrelated keys behind, respectively) against the fixed finalize promotes the just-landed key and pulls the drifted-but-safe keys forward in one commit, with no second PR opened; a refusal caused by the promoted story's *own* key disagreeing with the twin still stops and names it, unchanged; `pyforge-marshal-test` green.

## Constraints

- **Wrap, never absorb.** The harness is a declared runtime dependency — never vendored, never forked, never patched in place. Marshal owns provisioning, supervision, gates-as-objects, landing, status and portability; it does **not** own the dev/verify/review/commit engine. Decided on evidence, not preference: the harness is already conda-packaged here so absorbing buys nothing on distribution, and every known gap sits *outside* the engine. Revisited only on the recorded fork triggers (upstream stall, unadaptable contract break, a declined load-bearing fix, or a licence change away from MIT).
- **Exactly one harness seam.** One module may invoke the harness binary, import its package, read its policy file, or parse its output; everything else depends on the port. An import-linter contract fails the build on any other reference. This is what makes the fork fallback a bounded swap rather than a rewrite — it is a requirement, not a style preference.
- **Marshal is harness, never Skill.** No module makes a model call, loads a skill, or reads agent-authored prose as instruction; Marshal consumes only structured artifacts (specs, feeds, journals, exit codes, path sets). A test asserts no LLM client is importable from the package. The thing that governs the agent cannot be a thing the agent authors.
- **Pure decision core, impure edge.** Everything Marshal *decides* is a pure function over values with no I/O and no clock; everything Marshal *touches* sits behind a port with one adapter. Dependency direction is one-way and absolute. Decisions must be reproducible and testable without a running agent.
- **Never false-green; unevaluable *is* failure.** One owner of the verdict lattice and its projection to exit codes; no module constructs an exit code independently. There is no code path from "could not determine" to "clean", and no story reaches a merged state without both a green verify and a passing scope check.
- **The supervisor observes from outside and never trusts self-report.** A separate OS process parented to neither the agent session nor the invoking shell, taking only externally observable inputs, that the session cannot disable, silence or starve. Every enforcement ceiling's stop condition must be reachable from externally-observed quantities alone — a wedged session must never be its own witness. Supervisor liveness is itself journaled; a dead supervisor is a reported condition, not silence.
- **The journal is the single source of run truth, written before the act.** Every observable run fact is an entry; any irreversible or externally-visible action appends `intent` before and `outcome` after; appends are single atomic writes so a kill cannot lose the record of an action that happened. Self-owned by necessity — vendor retention runs 48 hours to 180 days and agent transcript formats change between versions.
- **Truth is partitioned by domain.** Git is the sole authority for repository facts (merged, tree revision, branch existence, commit subject); the journal is the sole authority for process facts (transitions, verdicts as evaluated, escalations, consumption, supervisor actions). No derived artifact sources one from the other, and a disagreement is **reported**, never silently reconciled.
- **Allowlists narrow only — the governed agent never authors the allowlist it is judged against.** The effective surface is the intersection of the policy-declared surface and the story-declared one; a declared path outside the policy surface is a hard finding, never an expansion. Story specs are machine-drafted, so freeze declarations, freeze removals and gate-mode changes never come from an agent-writable artifact. Allowlist always, never denylist — a permission file is not a security boundary. *(Amended 2026-09-09, closing F-5:)* under gate modes `none` and `per-epic` there is **no unattended mid-run freeze writer, by design** — the policy seed is the only unattended freeze source, and a mid-run freeze declaration or removal **requires per-story approval**. That a standalone gate evaluation cannot see a mid-run freeze (`cli/gate.py:831`) is therefore a correct scope statement, not a gap.
- **The trust model is declared, and in v1 it is advisory.** *(Declared 2026-09-09, closing F-4.)* The escape hatch for privileged changes is an operator-attributed journal entry admitted at the **call surface only** (`core/journal.py:159`). No authentication primitive exists in the package, the worktree is not a sandbox, and process isolation is deferred — so **v1 trusts the governed agent and the attribution guarantee is advisory, stated as advisory rather than claimed as a boundary**. The contract: attribution becomes **unforgeable before the Track (`hub:CAP-3`, Story 33.4) serves a second principal**. Vessel Story 33.11 (Epic 33, deps S-33.4) is minted `blocked` on its trigger — a Foundry cutover flag, a shared Hub, or an external adopter — so it never jumps the throughput queue.
- **Promote before teardown, and durable off the disposable ref.** A story spec counts as promoted only when its bytes exist at the canonical archive path in a commit reachable from a ref that survives the loop home; teardown's refusal predicate is reachability computed at teardown time, never a journal flag. Merely staged, or committed only on the disposable branch, is not promoted.
- **The loop home is the unit of isolation and the write boundary.** Marshal writes only to the loop home, the canonical Tier-3 store reached through its backlink, explicitly-named promotion targets, and one enumerated machine-scoped path. It never edits another project's artifacts or a shared repo-level file, and `main` is never checked out in a second working tree — loop results publish by push or batch PR.
- **Policy is composed once, materialized, immutable for the run, and carries per-key provenance.** Precedence is fixed — Marshal defaults → project policy → invocation flags, last wins — with no fourth layer and no per-key reordering. A mid-run change requires a new composition landing as an explicit decision entry, never a silent swap under a live supervisor. *(Amended 2026-07-31:)* site-wide enterprise configuration is **materialized into the defaults layer at install time** — never a runtime layer — so composition stays three-layer and pure in air-gapped deployments; and the project's **tool surface (MCP servers) is policy-declared** and rendered into the loop home at init on the adapter-seed pattern, probed at preflight; the user-scoped registry is never touched.
- **Marshal sequences on verdicts it never authors** *(ratified 2026-07-31)*. Inter-station gating consumes each station's durable, schema-validated verdict artifact, pinned to the tree revision it judged — Marshal never runs the judge and never alters a verdict. Verdict READS, not station invocations, are the gating mechanism; the composed route-verb surface belongs to the `spec-one-front-door` derivation, not this contract.
- **Shared Tier-2 writes serialize at the integration boundary** *(ratified 2026-07-31, dissolving the "mutex engine" question)*. Tracked planning artifacts are per-worktree copies whose publication serializes through git's push/batch-PR boundary; **regenerated surfaces (sprint feed, console) are re-derived on `main` after landing, never merged from homes** — append-only inputs merge, derived outputs regenerate. Appends to the genuinely shared canonical Tier-3 store take an advisory file lock. The journal's two-writer protocol is Open Question F-6's remedy, unchanged.
- **Escalation knowledge flows by pull, never cross-boundary write** *(ratified 2026-07-31)*. A resume against a resolved escalation records a reference to the resolving decision/artifact in the journal; knowledge-station ingestion reads journals from its own side of the boundary. No Marshal code path writes into another station's artifacts.
- **Detached is the default execution mode.** Run and resume detach from the invoking shell's lifetime and return a run identifier; foreground exists only behind an explicit flag documented as unsafe for resumes. Nothing in Marshal blocks on a run's completion.
- **Adapter behaviour comes from the declarative profile, never code branching.** Binary name, skill-tree path, seed files, first-run requirement and bypass semantics are all read from the profile plus the probe record. No `if adapter == "…"` branch exists; an unknown adapter is handled generically or reported unevaluable, never a crash.
- **Every run has a ceiling, and governance is structural rather than conversational.** There is no unbounded mode, and every hard limit is expressed as configuration or a deterministic check — never as an instruction to the agent, because conversational safety instructions do not survive context compaction.
- **Redaction is a port-boundary property, applied once.** Every port emitting bytes to a durable or third-party sink is a declared egress port routing through a single redacting serializer; no call site redacts, and no credential, token or key reaches a journal, gate record, probe record, PR body or commit.
- **One envelope for every command; machine-readable everything.** Identical envelope shape with coded findings from one central registry; human rendering is a pure projection, so no human-only information exists. Codes are never reused or renumbered.
- **Substrate and distribution posture.** Offline by default with network use never silent; linux-64 and osx-arm64 for v1 with Windows WSL-only and stated as such rather than silently failing; lean, conda-forge-available direct dependencies declared rather than inherited; the harness pinned to a declared supported range enforced at runtime.
- **No destructive default, no AI attribution.** Marshal never force-pushes; teardown refuses on unmerged work absent an explicit flag; mutating commands are idempotent and converge on re-run. No co-author trailer, model line or generated-with line is ever emitted — a commit trailer is part of the permanent authorship and blame record.
- **Acceptance is deterministic and machine-checkable end to end.** Exit codes, journal entries, gate records and git history are the oracle — never an agent's assertion that it passed.

- **The seed installer's own constraints, folded in 2026-08-02 (own architecture AD-51..AD-59; see the architecture doc's "Part II — The seed installer" section).** Two are flagged as contradicting Marshal's own constraints above rather than silently resolved — see the two CONTRADICTION notes inline below; neither is decided by this consolidation:
- **Five artifact classes, a closed set** — `referenced` · `copied-managed` · `copied-seeded` · `generated-derived` · `hybrid-managed-region`. REFERENCED is never materialized (version range only); COPIED·MANAGED is tool-owned and regenerated wholesale; COPIED·SEEDED is written once and repo-owned forever; GENERATED·DERIVED is recomputed every run; HYBRID·MANAGED-REGION is a repo-owned file with a tool-owned marker span, of which only the span is replaced. **Classification rule:** by *who must be able to change it* and *how an installed repo takes a later model upgrade for it*. The Dream's three-way split was one class short — "copied" must divide into MANAGED and SEEDED, because that is exactly what decides whether an upgrade may rewrite a file. Per-artifact V1 assignment: `extraction-manifest.md`.
- **The never-write set is structural** — `docs/dreams/*.md` (except the one `init` seed), `**/planning-artifacts/**` (except the `init`-seeded `specs/README.md`), `**/implementation-artifacts/**`, `docs/specs/*.md` (legacy tier), and `_bmad/bmm/**` + `_bmad/core/**` (installer-owned). Upgrading the model can never touch the work made with it.
- **The never-write guard lives at the lowest write primitive, not at call sites.** Every byte written to a target repo passes through one `fs` module holding an immutable path set frozen at construction; each write resolves to an absolute, symlink-resolved path and matches against the set *before* opening anything — unresolved matching would miss `_bmad-output/planning-artifacts`, which is a symlink into a project's Tier-2 tree. An AST meta-test enumerates write calls outside `fs`, so no future code path can route around the guard. Templates write through `fs` like everything else: a template that writes outside its declared paths is a hard error.
- **AD-51 — ~~CLI is typer + rich~~ → CLI is argparse, one tree, one binary.** *(RESOLVED 2026-08-08; superseded text kept below.)* The installer's verbs render through the same argparse tree every shipped Marshal command already uses. The superseded AD read: *"CLI is typer + rich, confined to `cli.py`. No other module imports either, so `--json` output and library use stay presentation-free. Plan rendering is the product's main human surface, so warden's argparse minimalism is deliberately not adopted."* Its presentation-free constraint survives verbatim and is the part that mattered; only the framework changed.
  - **✅ RESOLVED 2026-08-08 — argparse, decided on measurement.** The contradiction as flagged: Marshal's own CLI is argparse (architecture Structural Seed; Story 1.1 shipped `core/{model,findings,verdict}.py` + `cli/` on argparse), AD-51 specified typer + rich for the installer's unbuilt CLI, and the 2026-07-31 operator decision folds the installer's verbs into the `marshal` binary — so one framework must win. **Measured 2026-08-08:** the shipped tree carries **14 argparse subparsers** (`config init homes preflight teardown gate factory deploy land retire status check adapters upstream`) across ~34.2k LOC and 50 done stories, and **zero occurrences of `typer` anywhere under `src/`**. Migrating a shipped 50-story CLI to accommodate 36 unbuilt stories inverts the evidence. AD-51's actual concern — that plan rendering is the product's main human surface — is a *rendering* requirement, not a framework one, and is met by the existing envelope projection (human rendering is a pure projection of the machine-readable envelope, already a Marshal constraint above). **argparse wins; `rich` is not adopted.**
- **AD-52 — one Genesis-owned state file at `.genesis/state.yml`.** Copier's answers file is opaque and tool-owned: never read by Genesis, written only via Copier. Answers are re-supplied programmatically from Genesis state on every Copier call, so Genesis state is the single source of truth and the answers file stays an implementation detail.
- **AD-53 — one canonical marker grammar, rendered per comment syntax.** The format is *declared* per artifact in the manifest, never sniffed from content; the marker `sha` covers the region body only, so the marker line is not self-referential; nested or overlapping regions are a hard error.
- **AD-54 — `marshal seed check` re-implements the generic subset of this repo's `bmad_drift_check.py`; it does not import, vendor, or extract it.** It borrows the proven design (the `Finding` shape, the HARD/DRIFT/INFO ladder, the coverage check, `--json`). Roughly 85% of that 662-line script is `local-recipes` factory-specific and meaningless elsewhere. The two detectors coexist; convergence is explicitly out of V1, which keeps `local-recipes` uncoupled from a Genesis release.
  - **✅ RESOLVED 2026-08-08 — the installer's verbs live under a `seed` noun group; no verb is renamed or overloaded.** The contradiction as flagged: FR-65/AD-50 (shipped 2026-08-01, after AD-54/CAP-13 was authored) built a **different** `marshal check` that *routes to* `scripts/detectors.py`'s registry — "a route, not a reimplementation" — while AD-54 rules exactly that out for the installer's own `check`. The flag's own analysis contained the answer: **the two verbs answer different questions** (Marshal's — does *this* repo pass its own detector registry; the installer's CAP-13 — does an *installed, external* repo still conform to the model it adopted), so they were never one verb needing reconciliation. They are two verbs that collided only because both were about to be spelled `check` in one binary. Same for `init`: `marshal init <slug>` provisions a loop home *in this repo* (shipped, Story 1.4), while the installer's `init <path>` creates a *new repo elsewhere* — different objects, slug versus path.
    **Decision:** the installer's surface becomes `marshal seed <verb>` — `seed init <path>` · `seed adopt <path>` · `seed check <path>` · `seed update <path>` · `seed explain <artifact>` · `seed version`. This matches the noun-group shape six shipped commands already use (`config`, `gate`, `factory`, `deploy`, `adapters`, `upstream`), leaves `marshal init` and `marshal check` untouched with their shipped meanings, and needs no renaming of anything that already works. The group noun is the Charter's own word for this thing — § *Satellite: The Seed* — so the concept survives the retirement of the name `genesis` rather than being renamed twice. AD-54's substance (the installer's checker re-implements the generic subset rather than importing `bmad_drift_check.py`; the two detectors coexist; convergence stays out of V1) is unchanged and uncontradicted, because it was never about the same verb.
- **AD-55 — the manifest is one YAML document, keyed by stable artifact id, never by path** (paths are per-repo). Each entry carries class, path, format, regions with anchors, `since`/`until` model-version bounds, `applies_to`, and rationale. One file keeps coverage a single-pass check and makes the manifest reviewable as a diff — which matters, because the manifest *is* the product's contract.
- **AD-56 — region insertion uses a declared ordered anchor list with an append-at-EOF fallback, and never guesses mid-file.** It never inserts inside a fenced code block, and always reports the chosen anchor in the plan so a human reviewing the plan can veto placement.
- **AD-57 — the plan is a machine-readable artifact at `.genesis/plan.json`, gitignored by default**, carrying a `repo_fingerprint` (git HEAD + dirty flag + hashes of the artifacts it names); apply **refuses** a plan whose fingerprint no longer matches. Deliberately not committed: a plan is cheap to regenerate, while a committed stale plan is a hazard.
- **AD-58 — no `eject` verb ships in V1, but state must not preclude one.** For every managed artifact, state records `id`, `path`, `class`, `body_sha`, and `inserted_region_span` — enough for a future eject to strip markers and forget the artifacts without touching content.
- **AD-59 — legacy conventions are preserved, recorded in `state.legacy[]`, and at most advised** (an INFO finding naming the successor); never migrated, never written to. Genesis ships no automated Tier-1 → Tier-2 migration: legacy content is the team's work product and falls inside the never-write set.
- **One pipeline for every mutating verb:** `resolve → detect → plan → apply`. `check` is `adopt`'s detect+plan with the apply stage structurally unreachable — which is why "check never writes" is a guarantee rather than a discipline. Detect is pure (no I/O side effects); apply consumes only a serializable plan and never re-derives state; hash guards are evaluated in detect and never in apply.
- **Managed-region replacement is pure byte-span substitution** between markers — never a three-way merge, never semantic markdown parsing. A half-merged file and a conflict marker are therefore not representable states.
- **Idempotence is *defined* as plan-emptiness:** a verb is idempotent iff detect+plan immediately after a successful apply yields zero actions. This makes the `local-recipes` oracle and adopt-run-twice the same assertion against different repos — one mechanism, two proofs.
- **The empty-plan oracle runs in Genesis's own CI**, so model drift in the repository the model was extracted from fails Genesis's build the day it appears, rather than at the next install.
- **Copier is a dependency, not a framework.** Exactly one module imports it, and only its public `run_copy` / `run_update` / `run_recopy`; pinned `>=9.17,<10` by range with a version-range sync test. `--force` maps to `run_recopy` semantics (discarding local evolution of managed artifacts) and requires explicit confirmation. Copier's code-executing template features stay gated behind an explicit `--unsafe` flag.
- **`adopt` and `update` are dry-run/two-phase by default and refuse on a dirty git worktree**, because git is the designated undo mechanism. No verb may leave a repo partially applied: apply is transactional per plan, or it reverts. State is written **last**, after all file writes succeed, in one atomic replace — the `bmad-switch` marker/symlink desync lesson encoded.
- **Two clocks:** CLI semver and operating-model semver move independently, are both recorded in state, and are both reported by `marshal seed version`. Migrations are keyed to model version only, are pure plan-producing functions that never write directly, and are applied exactly once.
- **Genesis installs the machinery; Marshal operates it.** Marshal owns the *source* of `scripts/bmad-switch` and `scripts/bmad-loop-worktree`; Genesis owns their *delivery* as COPIED·MANAGED artifacts and never forks them. Genesis's write scope is a repo's structure and conventions; Marshal's is a repo's executions.
- **Air-gap by construction:** no module imports `requests`, `httpx`, or `urllib.request` (meta-test enforced); templates ship in-package; the only network path is Copier's git fetch behind an explicit `--template <url>`. Accepted trade-off: a model change requires a package release, and `--template` is the escape valve.
- **Packaging clones `pyforge-warden`'s shape exactly** — pixi workspace member, hatchling, `packages = ["src/pyforge"]`, a `genesis` console entry point, and a **lean** environment with `no-default-feature = true`. The lean env is mandatory, not cosmetic: bmad-loop worktrees materialize it, never the fat `local-recipes` env. Python `>=3.12`; `pyforge.genesis` shares the `pyforge` namespace with warden and atlas.
- **Touching root `pixi.toml` fires this repo's two always-on PR gates** (the `maintenance` label and a regenerated `environment.yaml`) and stales `docs/reference/library-llms-full.md`; all three are acceptance criteria on the packaging work, not follow-ups.
- **Genesis's own artifacts obey the tier discipline it installs:** planning artifacts are Tier 2, story specs are durable and tracked under `planning-artifacts/specs/`, and nothing it produces may be git-tracked under `implementation-artifacts/`.
- **Every finding type is a member of one enum with a documented remedy string**; ad-hoc error strings are forbidden, and non-zero exit codes are distinct and documented per failure mode.
- **Merged-tree re-verification is a second run of the station's own `verify_commands`, never a new gate** *(2026-09-19, CAP-249)*: marshal materialises the tree git would produce and re-runs the existing verify against it; it never performs the merge, never adds a verdict owner, and git stays the sole authority for the merge result — the one verdict lattice projects the outcome (extends "Never false-green; unevaluable *is* failure").

## Non-goals

- **Reimplementing the dev/verify/review/commit engine.** Marshal is the factory floor around it, not the engine.
- **Being a Skill.** Nothing in Marshal is LLM-authored or LLM-decided at runtime.
- **Judging its own output.** Station verdicts stay independent — the hand that builds is never the gate that judges. Compliance verdicts belong to Warden, toolchain health to Doctor, provisioning to Steward, communications to Herald.
- **A hosted control plane, remote telemetry, or an account.** Local-first; Marshal opens no port.
- **An IDE extension, chat participant, or marketplace artifact.** The sideloaded VS Code extension is out of charter; the `@bmad` Copilot-Chat adapter is a human-in-the-IDE surface, deferred and re-owned. *(Reaffirmed 2026-07-31: the enterprise-seam proposal that bundled IDE surfaces was dissolved — internal MCP servers route through the policy-declared tool surface, proprietary agent CLIs through adapter profiles, site policy through install-time materialization. No plugin-registry subsystem; this exclusion stands.)*
- **Any HTTP proxy against a vendor's inference endpoint.** Superseded: the upstream `copilot` profile drives the sanctioned CLI directly, and the proxy path is unversioned, reverse-engineered and abuse-detection-exposed.
- **Sandbox or container implementation.** Worktree isolation is in scope; process and network isolation is the provisioning station's territory. **A worktree isolates the filesystem and branch, not the process or network** — stated, not hidden. *(2026-09-09, F-4:)* this deferral is also why v1's operator attribution is advisory — see the declared trust-model constraint.
- ~~**PR-lifecycle automation beyond opening and updating a batch PR.**~~ **STRUCK 2026-07-31** by operator decision (`docs/dreams/pr-lifecycle.md`): Marshal owns the PR lifecycle — see CAP-9. The former boundary survives only as CAP-9's refusal semantics: no merge on a red required check, no silent force.
- **Fleet-level resource budgeting across concurrent runs.** Per-run ceilings only. *(Confirmed out of scope for v1 on 2026-09-09, closing Q-11:)* a cross-run budget would be the first thing to need shared mutable state across loop homes and therefore the first to break the loop-home write boundary. The v1 controls are the per-run and per-story ceilings (`core/policy.py:503-505`), `dispatch.max_parallel` for fan-out concurrency (fanout CAP-6, Story 33.8), and the wall-clock-plus-idle-strand dispatch signal with token ceilings advisory. Revisit only once Story 33.1's measured baseline exists.
- **ACP as the adapter contract.** Deferred behind a recorded revisit trigger; the harness's declarative profiles are the adapter contract until then. *(Trigger status recorded 2026-09-09, closing Q-13:)* trigger one — the harness gains an ACP client path — has **FIRED** upstream (bmad-loop 0.9.0 ships a sanctioned `copilot` profile plus `copilot --acp`), but **alone it does not start the migration**. Marshal waits for the schema to reach stable, or for two must-support adapters to ship ACP-only.
- **Windows-native operation.** Deferred on maturity, not availability.
- **OpenTelemetry `gen_ai.*` emission.** Deferred on evidence — the conventions moved repositories in June 2026 and remain Development-stability with live attribute renames. The run journal carries equivalent information in a self-owned format. *(Deferral condition named 2026-09-09, closing Q-12:)* deferred **until the semantic conventions reach stable**; the Track publisher (Story 33.4) is v1's telemetry seam and maps to `gen_ai.*` later without re-instrumenting.
- **Formal L1–L5 story-mode labelling beyond the gate-mode mapping.** Frontier.
- **Claiming to be "the orchestrator."** Marshal is the station around one, and positioning must stay honest about it. *(Scope clarified 2026-07-31: this targets the engine claim — bmad-loop remains the dev/verify/review/commit orchestrator. It does not bar Marshal from sequencing on other stations' verdicts, which it consumes and never authors; see the sequencing constraint.)*

- **The seed installer's own non-goals, folded in 2026-08-02:**
- **Operating the machinery Genesis installs** — bmad-loop runs, quality gates, escalation, graduated autonomy, worktree lifecycle, and run-time project switching are Marshal's.
- **Machine and toolchain health** — Genesis performs a minimal presence-and-floor probe of REFERENCED dependencies (so it works in a repo that has not adopted Doctor) and delegates to `doctor check` when available, rather than growing its own probe suite.
- **Deck content, and the Dream's other two faces** — the Dream casts Genesis as three things: the master narrative, the alignment deck (`presentations/pyforge-genesis/`, already real), and the seed. **This contract covers only the seed.** Genesis lays down `presentations/<slug>/` and its conventions; Herald fills and round-trips them.
- **Repository creation on a git host** — `marshal seed init` makes a tree, not a GitHub repo.
- **Non-git targets** — they forfeit the update story entirely, which is the whole product.
- **Composable feature modules** (adopting a subset of the model) — V1.x; the manifest's `applies_to` field is shaped to allow a future `groups[]` without a schema break.
- **`check --fix`** — V1.x; requires a fixable/unfixable distinction per finding type.
- **`marshal seed eject`** — V1.x; state is shaped for it but no verb ships.
- **A hosted registry of installations or fleet conformance scorecards** — Genesis is not a service and keeps no central record; installed repos run `check` in their own CI.
- **Publishing the model as a separately versioned artifact** — V2; `--template` is the seam.
- **Automated Tier-1 (`docs/specs/`) → Tier-2 migration** — preserve and mark only.
- **Converging `marshal seed check` with `bmad-drift-check`** — explicitly out of V1.
- **Windows parity beyond `init` / `check`** — best-effort; the loop machinery is Linux/macOS, Windows via WSL.
- **Authoring any conda recipe** — `copier` is consumed from the existing conda-forge feedstock, so the core work triggers neither the CFE skill-invocation rule nor its closeout retro.

## Success signal

An operator launches a wave against an approved spec, goes to bed, and wakes to merged code plus a complete paper trail nobody had to remember to file: **no story merged without a green verify and a passing scope check**; **every unattended run terminated as completed, escalated, or stopped-with-a-named-reason, with zero idle-strand-to-cap events**; and **every merged story's spec promoted into tracked artifacts with no human action** — while several loop homes ran concurrently with isolation verification passing and at least two adapters hold a dated passing conformance row. Each verdict reads from exit codes, journal entries and git history alone.

Deliberately **not** optimized, and tracked as counter-metrics: raw story throughput (optimizing it reproduces the documented failure of agents spending days on impossible solutions), adapter count (two proven beat six claimed), and reduction in escalation count (fewer escalations is only good if precision holds — driving the number down by widening what the agent guesses at is the exact failure this product exists to prevent).

**The seed installer's own success signal, folded in 2026-08-02** (a second, independent success criterion — the two are not merged into one statement because they measure different things: Marshal's above measures a wave of stories landing unattended; this one measures a second repository being installed and upgraded):

A second repository, created by `marshal seed init`, runs a full Dream → spec → epics →
loop-driven build and then **takes a later model upgrade via `marshal seed update` with no hand
edits** — `marshal seed check` green before and after. Alongside it, `marshal seed adopt --dry-run`
against `local-recipes` at the shipped model version produces an **empty plan**, proving
the model Genesis carries and the repository it was extracted from are the same model.
Both verdicts read from exit codes and produced files alone.

The signal has two named falsifiers, and reaching either pauses or rescopes the work
rather than shipping around it: **K-01** — the managed-region merge proves unreliable on
real files (corruption or an unresolvable conflict in either of the first two adopters);
**K-02** — the empty-plan oracle cannot be reached without special-casing the model into
incoherence, which would mean the model is not actually extractable and the Dream's
stabilization gate was called too early.

## Assumptions

- The reference customer is this factory and its operator; success criteria are drawn from live operational evidence, not customer interviews.
- The upstream harness remains actively maintained — it moved a full minor version inside the adoption window. The recorded fork triggers are the stated mitigation.
- BMAD Method artifact conventions (sprint feed, epics document, the Tier-2/Tier-3 split) remain the story-feed contract.
- linux-64 and osx-arm64 are the supported hosts for v1; Windows is WSL-only.
- The local conda channel is acceptable for v1 distribution; the harness is packaged in this repo but not yet on conda-forge.
- The idle-strand threshold defaults to 25 minutes, carried from the hand-written watchdog that worked in production.
- Where the harness supports only run-level model selection, batching stories by tier is acceptable v1 behaviour; a per-story key is an upstream request.
- Performance envelope: `init` and `status` under 10 seconds on a warm checkout, supervisor poll ≤ 60 seconds — and the poll interval must never exceed the active prompt-cache TTL, the documented mechanism behind the largest circulated cost overruns.
- 80% escalation precision is a first target absent a baseline.
- **Live-evidence counts cited across the chain are point-in-time and were already stale at review** (4 loop homes exist today, not 7; 93 skill directories, not 92). No capability contract may hard-code these numbers.
- CAP-251 prefers reading the promoted ledger from `origin/main` over moving the primary checkout: under the operator rule "never run git in a shared checkout" (2026-09-13) a checkout that is not a clean `main` belongs to someone else, so refusing by name is the correct outcome, not a degraded one.

**The seed installer's own assumptions, folded in 2026-08-02:**
- The seed installer targets git repositories only; non-git targets forfeit the update story entirely.
- The operating model has genuinely stabilized — the Dream's own gate. Evidence: pyforge-atlas shipped 32 stories and pyforge-warden 31 through it; the durable-story-specs convention closed the last known hole on 2026-07-25.
- Copier's `run_copy` / `run_update` / `run_recopy` signatures are stable across 9.x, and its answers-file path is template-configurable (the second is AD-52's fallback trigger). Both are gated by Spike-0, which is a critical gate on the materialization work rather than an accompanying task.
- HTML-comment markers are unambiguous in the specific markdown files the manifest names.
- The first two adopters are `local-recipes` (the oracle) and one greenfield pyforge sibling; external adoption is post-V1.
- Marshal accepts ownership of `bmad-switch` / `bmad-loop-worktree` *source* while Genesis owns *delivery*. This is not yet ratified in Marshal's own planning chain.

## Open Questions

**The chain's own architecture gate returned `BLOCKED-ON`** (adversarial review, 2026-07-25, against AD-25–AD-39: 6 CRITICAL · 12 HIGH · 11 MED · 3 LOW). The block was on six specific decisions, not on the design. **All six are closed as of 2026-09-09** — F-1, F-2, F-3 and F-6 resolved against shipped code by the disposition pass; F-4 and F-5 answered by the operator the same day — and each keeps its dated resolution below. Detail and the originally proposed remedies live in the adopted review companion. What remains open in this section is epic-scoped and installer-scoped: items 7, 8, 9 and the three folded seed-installer questions, which belong to their own epics.

> **Disposition pass — 2026-09-09 (operator-approved, fleet-readiness batch row mars-B-B13).**
> The `BLOCKED-ON` block had been carried in this body since 2026-08-02 and never dispositioned.
> Each of **F-1..F-6** and **Q-11..Q-16** was judged item by item against live code at
> `fe4025ea90`. **Retired as resolved or moot: F-1, F-2, F-3, F-6, Q-15, Q-16** — each keeps its
> text below, struck through, with a dated resolution. **Still live and HOISTED into the
> `open_questions:` frontmatter key: F-4, F-5 (narrowed), Q-11, Q-12, Q-13, Q-14** — until today
> every frontmatter-reading detector saw zero open questions on a Spec whose own body says its
> gate returned `BLOCKED-ON`. *Rejected: mark the whole block historical without per-item
> disposition — F-4 alone (an undeclared trust model behind operator-attributed journal entries)
> is still a live property of shipped code.*
>
> **Items 7, 8, 9 and the three folded seed-installer questions (K-03, "creates a repo or a
> tree", "append-at-EOF as a safe anchor fallback") are NOT dispositioned by this pass** — they
> are epic-scoped or installer-scoped and belong to their own epics. They stay in the body
> unchanged.
>
> **Answering pass — 2026-09-09 (operator), same day, closing the six.** Every item hoisted a few
> hours earlier was answered: **F-4** (the trust model is declared — advisory in v1, unforgeable
> before the Track serves a second principal, vessel Story 33.11), **F-5** (no unattended mid-run
> freeze writer, by design; per-story approval required), **Q-11** (a fleet-level budget is out of
> scope for v1), **Q-12** (OTel deferred until the conventions reach stable), **Q-13** (ACP trigger
> one has fired but does not alone start the migration), **Q-14** (the idle threshold stands until
> one wave is *read* from the dispatch journals). The frontmatter `open_questions:` key therefore
> **returns to `[]`**. Each answer is dated in place below, and the load-bearing ones are amended
> into **Constraints** (the declared trust model; the freeze-writer clause) and **Non-goals** (fleet
> budget, ACP, OTel) rather than living only in this section. **Body item 15** — where a story's
> declared difficulty lives, distinct from the verb-naming Q-15 — was answered in the same pass,
> closing the numbering discrepancy the prior pass flagged.

1. ~~**F-1 — composed policy has no path to the harness.** The pinned harness hard-codes its policy file path with no override flag; that file is git-tracked in this repo; loop homes publish by pushing to the integration branch, so a Marshal-written copy would bleed to every other project. One constraint forbids editing it while one requirement mandates editing it, and no story owns the conveyance. Decide the rendering path and its ignore status, and give it a story.~~

    **RESOLVED 2026-09-09.** `marshal config --write-harness-policy` shipped (`cli/config.py:327`) as Story 1.10 (ledger `1-10-render-the-harness-policy-from-the-canonical-effectivepolicy`: `done`). The rendering path and its idempotence are contracted at `adapters/harness_bmadloop.py:517`, `:568` and `core/harness_profile.py:830`, and `cli/spin.py:706` reads the last persisted render to detect divergence. The conveyance has a story and a boundary; the operator-facing form is `marshal config --write-harness-policy .` per loop home. **RETIRED from the block.**
2. ~~**F-2 — a quarantine clause legislates a false green** into the single source of run truth: "an unparseable line never makes the surrounding run state unevaluable" means a corrupt line that was the outcome recording a gate failure, escalation or freeze leaves the run reading clean. Replace with *scoped* unevaluability.~~

    **RESOLVED 2026-09-09 — replaced by SCOPED unevaluability, exactly as the finding demanded.** `core/journal.py` quarantines to the offending `(story, kind)` DOMAIN rather than the run (`:586`), surfaces it as a registered `MRS-JOURNAL-001`/`002` Finding under AD-8 ("unevaluable is a failure, never silently dropped", `:626`), and widens to the whole run only when a partial recovery carries no meaningful scope (AD-30, `:620-624`). The two live review findings that drove it are recorded in the code itself (`:586` the sidecar round-trip collision; `:925` the blank terminator that made an intact run wholly unevaluable). **RETIRED from the block.**
3. ~~**F-3 — standalone gate evaluation has no frozen set.** Non-run invocations mint into a namespace excluded from the run fold, while the frozen set is solely a product of that fold — so the "evaluate before approving, with no run in flight" journey can never exit 0. Define which journal a standalone evaluation folds.~~

    **RESOLVED 2026-09-09.** `cli/gate.py` is the standalone verify-command runner: `--run <id>` folds that run's real journal (`:41`), and a standalone invocation without one declares its own scope explicitly — `data["scope"] = "policy-seed-only"` plus `data["scope_note"] = "mid-run freezes not visible"` (`:826-831`), with the code citing AD-26/F-3 by name and AD-26's own resolution text ("a complete, legitimate answer on its own, not a degraded one"). The "evaluate before approving with no run in flight" journey now exits 0 against a declared, narrower scope. **RETIRED from the block.**
4. ~~**F-4 — the trust model is undeclared.** The escape hatch for privileged changes is an "operator-attributed" journal entry, but no authentication primitive is defined anywhere, the worktree is explicitly not a sandbox, and process isolation is deferred — so the governed session can invoke the CLI or write the record directly. Either state that the agent is trusted (and that the guarantee is therefore advisory), or specify what makes attribution unforgeable.~~

    **ANSWERED 2026-09-09 (operator) — the Spec now STATES the trust model; the finding is closed.** The question offered two exits and the answer takes both, in order. **A is the v1 state:** the governed agent is trusted and operator attribution is **advisory**, enforced at the CALL surface only (`core/journal.py:159` — still the one place in the package that names the concept), with no authentication primitive, no sandbox, and process isolation deferred **and named as deferred**. **B is the contract:** attribution becomes **unforgeable before the Track (`hub:CAP-3`, Story 33.4) serves a second principal** — the moment the guarantee stops being self-addressed is the moment it must become real. **Vessel:** Story 33.11 (Epic 33, deps S-33.4), minted `blocked` on its trigger — a Foundry cutover flag, a shared Hub, or an external adopter — so it never jumps the throughput queue. Rendered above as a Constraint ("The trust model is declared, and in v1 it is advisory").
5. ~~**F-5 — mid-run freeze accumulation has no writer in either production gate mode.** Under `none` and `per-epic` no operator is present and the story may not declare its own freeze. Name the writer, or state that mid-run freezes require per-story approval and amend the affected requirements.~~

    **ANSWERED 2026-09-09 (operator) — the finding's second exit is taken; the finding is closed.** The vocabulary and the writer constraint had already shipped — `KIND_FREEZE_DECLARED` / `KIND_FREEZE_REMOVED` (`core/journal.py:152-163`), declaring story key at `:655-656`, policy- or operator-attributed writes only at `:159`. The residue is answered by **declaring the absence deliberate**: under gate modes `none` and `per-epic` there is **no unattended mid-run freeze writer, by design**. The **policy seed is the only unattended freeze source**, and a mid-run freeze declaration or removal **requires per-story approval**. `cli/gate.py:831` — a standalone evaluation cannot see a mid-run freeze — therefore stands as a correct scope statement rather than a gap. The affected requirements are amended to say so; rendered above in the allowlist Constraint.
6. ~~**F-6 — a unique monotonic entry id is unachievable under the declared append protocol** (lock-free, uncoordinated, two writers by design), and the pairing and total-order rules both rest on it. Needs a composite id or a declared lock — plus a third phase value for the many entry kinds that are neither intent nor outcome.~~

    **RESOLVED 2026-09-09, exactly as the finding proposed.** `core/journal.py:13` documents a COMPOSITE `(writer_id, counter)` id — "a per-writer monotonic counter, never across the run" (`:201`) — serialized at `:229-233`, parsed at `:1024`, with the sidecar path derived from it at `:421-433`. The pairing and total-order rules now rest on a composite id rather than an unachievable global monotonic one. **RETIRED from the block.**
7. **Pre-Epic-1 amendment set** — cheap and mechanical, but each will mislead a builder on day one: an inverted story dependency (a scope-check story needs a fold from a later epic); two normative definitions of the story key, where the pinned harness's own CLI accepts a suffix one rule forbids and "normalized on read" never says whether the suffix survives; a missing per-epic policy-surface key with no benign default, so any epic lacking it is bricked; a superseded-but-untagged, now-false invariant still live in a document marked final; and two normative envelope definitions.
8. **Epic-scoped HIGH findings**, each a *confirmed* defect rather than a preference, resolvable at the head of the owning epic but none to reach implementation unresolved: conformance-matrix location contradicting its own requirement and the architecture's operational envelope; a seed-field read ban colliding with the requirement to print every effective key (both in one story's acceptance block); a classification function declared total over the code alone yet required to vary by command surface; a result state with no lattice member; a completeness check whose denominator is undefined and therefore vacuous; promotion durability requiring a network operation the offline-by-default rule does not enumerate, making offline teardown refuse every time; an egress criterion that captures the ports which must pass credentials to a child process; a redaction requirement needing a dependency edge the one-way rule never authorizes; and a permanently-open intent breaking the idempotent-converges-to-exit-0 property.
9. **Ownership of the cross-tool entry-file family** — the repo's own entry document assigns the portable handoff to Herald while the portability Dream records it as re-scoped to Marshal. One is stale. CAP-6 ships **detection only** and edits nothing until this is settled.
10. ~~Does Marshal own PR-lifecycle automation?~~ **RESOLVED 2026-07-31 (operator): Marshal owns it.** Input Dream `docs/dreams/pr-lifecycle.md`; contracted as CAP-9; the corresponding non-goal struck. Numbering retained for reference stability.
11. ~~**Should fleet-level resource budgets be v1 scope?** Per-run ceilings ship; cross-run budgeting would be the first thing to need shared mutable state and therefore the first thing to break the loop-home write boundary.~~

    **ANSWERED 2026-09-09 (operator) — a cross-run (fleet-level) resource budget is OUT of scope for v1.** The reason is the one the question itself named: it would be the first thing to need shared mutable state across loop homes and therefore the first to break the loop-home write boundary. The **v1 controls** are the per-run and per-story ceilings (`core/policy.py:503-505`, read at `core/dispatch.py:257-259`), `dispatch.max_parallel` for fan-out concurrency (`spec-marshal-parallel-dispatch-fanout` CAP-6, Story 33.8), and the wall-clock-plus-idle-strand dispatch signal with token ceilings advisory (`spec-marshal-single-story-dispatch` OQ-3). **Revisit only once Story 33.1's measured baseline exists** — not before. Rendered above as a Non-goal.
12. ~~**Is OpenTelemetry `gen_ai.*` emission worth v1 cost** given the conventions remain Development-stability with live attribute renames?~~

    **ANSWERED 2026-09-09 (operator) — deferred, with the resumption condition now named.** Emission waits **until the semantic conventions reach stable**; paying v1 cost against Development-stability attributes that are still being renamed buys instrumentation that must be redone. The deferral is cheap to hold because **the Track publisher (Story 33.4) is v1's telemetry seam** and maps to `gen_ai.*` later **without re-instrumenting**. (Verified 2026-09-09: zero occurrences of `gen_ai` or `opentelemetry` anywhere in the package.) Rendered above as a Non-goal.
13. ~~**What triggers migrating the adapter layer to ACP?** Proposed: the harness gains an ACP client path, *or* two must-support adapters ship ACP-only, *or* the schema reaches stable with the Claude adapter's known gaps closed.~~

    **ANSWERED 2026-09-09 (operator) — trigger one is recorded as FIRED, but one trigger alone does not start the migration.** bmad-loop 0.9.0 shipped a sanctioned `copilot` profile plus `copilot --acp`, so the harness has gained an ACP client path — while pyforge-marshal itself still contains zero `acp` references. **Marshal waits for the schema to reach stable, OR for two must-support adapters to ship ACP-only.** The firing is logged so the next trigger is judged against a known count, not rediscovered. Rendered above as a Non-goal.
14. ~~**Does the 25-minute idle threshold false-positive on legitimately slow verify steps?** Needs one wave of data.~~

    **ANSWERED 2026-09-09 (operator) — the threshold stands, and the wave becomes an acceptance clause rather than an experiment.** The 25-minute default (`core/policy.py:475` `idle_threshold_minutes = 25`, validator `:1375-1392`, Story 3.5 / FR-12) **stays** — it is real, operator-tunable through the normal policy layers, and no station overrides it. It is revisited only after **one wave of per-session timing is READ from the dispatch journals** (`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/*/journal.jsonl`), which now carry that timing at source. That read is **an acceptance clause on Story 33.1**, not a study anyone has to schedule.
15. ~~**Where does a story's declared difficulty live** — story-spec frontmatter or the epics document? CAP-7 reads it through one accessor so this can be settled without reshaping tiering.~~

    **Q-15 (verb naming) RESOLVED 2026-09-09 and RETIRED from the block.** `marshal factory dispatch` is the shipped verb and there is no `marshal dev` family; the branch grammar `dispatch/<project_slug>/<key>` is a shared-spine constant (`pyforge-core` `landing_evidence.py:50`) consumed by doctor, so renaming would break a cross-package grammar (closed on `spec-marshal-single-story-dispatch` OQ-1; this Spec's Q-15 inherits that answer).

    **The difficulty-location question — this body's item 15 as written — ANSWERED 2026-09-09 (operator), closing the numbering discrepancy the earlier pass flagged.** The two questions are genuinely distinct and both are now answered: number 15 denotes *verb naming* in `spec-marshal-single-story-dispatch` OQ-1 and PRD Q-15 (resolved immediately above), while **this body's item 15 asks where a story's declared difficulty lives — and it lives in the story spec's frontmatter `difficulty:` key.** Evidence: 57 story specs declare it today and `model_tier_map` reads it from there (adaptive-model-tiering, verified 2026-09-09). CAP-7's single accessor is unchanged, so nothing about tiering reshapes. Not hoisted — answered in place.
16. **What minimal story exercises spec → change → verify → commit** while staying adapter-agnostic and cheap enough to serve as the conformance smoke?

    **RESOLVED 2026-09-09 — RETIRED from the block.** Story 6.5 "conformance smoke in an ephemeral home" is `done` (ledger `6-5-conformance-smoke-in-an-ephemeral-home`), and the pinned smoke story `1-1-marshal-conformance-smoke` is the artifact the token-economy benchmark (Story 33.1) records its off-leg and on-leg against — adapter-agnostic and cheap, exactly as the question required.
17. ~~**Installer verb mapping**~~ — **RESOLVED 2026-08-08. The installer's verbs live under a `seed` noun group.** *(Raised 2026-07-31, enriched 2026-08-02.)* As posed: the installer folds into the `marshal` CLI (Epics 10–12), but its `init` collided with the shipped `marshal init <slug>`; and a second collision surfaced at the 2026-08-02 consolidation — `marshal check` (FR-65/AD-50, shipped 2026-08-01) routes to `scripts/detectors.py`'s registry and answers *"does **this** repo pass its own detector registry?"*, while CAP-13 answers *"does an **installed, external** repo still conform to the model it adopted?"* — same verb name, different scope, one binary.
    **Resolution:** the question contained its own answer. Both pairs were never one verb needing reconciliation; they are two verbs that collided only because both were about to be spelled the same. `marshal init <slug>` takes a **slug** and provisions a loop home *in this repo*; the installer's takes a **path** and creates a repo *elsewhere*. Rather than rename either shipped verb, the installer's surface becomes `marshal seed <verb>` — `seed init` · `seed adopt` · `seed check` · `seed update` · `seed explain` · `seed version` (+ `seed eject`, V1.x) — matching the noun-group shape six shipped commands already use, and taking its noun from the Charter's own § *Satellite: The Seed* so the concept outlives the retired name `genesis`. Nothing shipped is renamed; no verb is overloaded. The 19 installer story keys carrying the old verb names are renamed in the same pass (all are `backlog`; no `done` key is touched). See AD-51 and AD-54 above for the two contradiction resolutions this closes.

*Wrap-versus-absorb is deliberately absent here: it was resolved in the chain and is carried as the first Constraint, with the recorded fork triggers as its revisit path. Five further capability questions raised by the 2026-07-31 architecture audit (Tier-2 serialization, tool-surface brokering, escalation knowledge, the enterprise seam, inter-station sequencing) were resolved by operator ruling the same day and are rendered above as constraints, CAP-9, and non-goal reaffirmations — the memlog carries each decision.*

**The seed installer's own open questions, folded in 2026-08-02** (distinct numbering `K-03`/`OQ-*`, not merged into the numbered list above):

- **K-03 has no quantified threshold in any source.** At what migrations-per-model-minor-version rate does the model become too volatile to install, and who makes that call?
- **Does `marshal seed init` create a repository or only a tree?** Creation on a git host is scoped out, but a local `git init` and first commit are left unstated.
- **Is append-at-EOF always a safe anchor fallback?** AD-56 chose the fallback for an unmatched anchor, but did not close whether an unfamiliar `CLAUDE.md` deserves a refusal instead.
