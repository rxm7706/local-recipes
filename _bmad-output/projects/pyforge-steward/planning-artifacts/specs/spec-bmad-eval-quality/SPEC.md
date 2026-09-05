---
spec: bmad-eval-quality
status: ready
owner-dream: docs/dreams/bmad-eval-quality.md
surface:
  - recipes/bmad-eval-quality/**   # CAP-1 lands in the same PR as this Spec
  # - evals/review-catches-planted-defect/**   # claim when CAP-2 lands
companions:
  - packaging.md
  - pilot-contract.md
sources:
  - ../../../../../../docs/dreams/bmad-eval-quality.md
assumptions:
  - "noarch: generic with a nodejs >=22.20.0 run floor (the bmad-method recipe's class) is
    acceptable for the first cut although the Dream says per-arch — no native code, one prod
    dep (zod); decided at recipe time with conda-forge-expert."
  - "corpus/dev/contracts/satisfied-declarations.json is the canonical complete contract example
    (Dream § Grounding) and is CAP-1's compile-test target; verified at recipe time."
open_questions:
  - "Where does the CAP-2 driver run its Claude calls from — the local-recipes pixi env or a
    dedicated eval env — and which station's [adapter.review].model is the reference?"
  - "How is a CAP-2 trial's cost recorded fleet-wide — steward budget (44.15 Actions-minutes
    metering) or a local ledger under evals/?"
  - "Which pixi environment carries bmad-eval-quality for daily use — local-recipes (default) or
    only bmad-suite-full?"
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale this contract intentionally omits.

# SPEC — eval-quality joins the bmad-suite, and a first contract proves the reviewer looks

## Why

The factory runs unattended: with `gate_mode = "none"` the independent reviewer is the only
safety net a bmad-loop story passes, and nothing measures whether it would catch a real defect —
every other quality surface is deterministic or an unproven LLM review, and the repo's memory
records the failure class (fail-open detectors, a false-fact `[reject]` hiding a finding, a fork
ignoring review scope). `eval-quality` (bmad-code-org) grades *evaluations* by a twin-run loop —
one contract against a clean system and one with a single planted defect — and executes nothing
itself. A pain to solve, for the fleet operator; the backdrop is a growing unattended run count
with zero evidence about the last line of defence.

## Capabilities

- **CAP-1 — Suite membership.** *Intent:* `eval-quality` installs the suite's way as a
  `bmad-suite` member (recipe, manifest line, pixi pin, channel) so every fleet consumer gets
  the 0.2.0-line binary that has `score`. *Success:* `recipe-build` green; `eval-quality
  --version` prints `0.2.0`, `--help` lists `score`, `compile` on a shipped corpus contract exits
  0; enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml` (auto-flows to metapackage
  run deps, doctor's drift watch, steward's pipeline-truth); pixi pin `bmad-eval-quality
  >=0.2.0.dev0` with `environment.yaml` regenerated; baseline pin set, install-matrix,
  install-class and `library-llms-full.md` rows present; the PR carries `maintenance`.
- **CAP-2 — Pilot contract `review-catches-planted-defect`.** *Intent:* one Behavioral
  Evaluation Contract, run twin-arm (clean vs one planted `file:line` defect) against the
  `edge-case-hunter` review layer bmad-loop relies on, yields a catch rate the fleet can read.
  *Success:* the contract compiles; a one-trial twin-run preflights both arms, the mutated arm's
  review cites `pkg/discount.py:17` and the clean arm does not; three trials per arm yield a
  policy-comparable strength vector with a catch rate; pixi tasks `eval-quality-smoke`,
  `eval-quality-review-twin-run -- --trials N`, `eval-quality-review-replay` exist and are never
  wired into `detectors`.

## Constraints

- Dream-first and the CFE rules bind: the recipe goes through `conda-forge-expert` (Rule 1); the
  effort closes with a CFE retro (Rule 2).
- Exact commit pin (`0.2.0.dev0 @ 3172162fbdc7c4bb70ed11c1367dc3e433797535`); `version` and
  `commit` bump together; never a floating HEAD; flip to tag-mode the day `v0.2.0` lands. A
  schema mismatch fails `compile` loudly — never papered over.
- The pilot measures the reviewer; it is not a PR gate. Warden stays the sole PR verdict;
  nothing here joins `detectors` / `detectors-ci`.
- Every run is cost-bounded (`claude -p --max-budget-usd …`) with model and effort pinned to the
  station's `[adapter.review].model`; report catch-rate across trials, never one verdict.
- `spec-bmad-suite-channel-product` § Non-goals "packaging anything new" is deliberately
  overridden for this one member (operator, 2026-09-05). `suite-members.yaml` is the only
  enrolment list.
- Every contract models its system-under-test as an HTTP-shaped operation (schema v0 admits only
  `permittedInterfaces.kind = api`; cli/web/mcp fail compilation) — the driver is the adapter.

## Non-goals

- Installing TEA as a module (it stays a pinned suite member; not needed to author contracts).
- Evaluating the whole `bmad-build-auto` review skill end-to-end — its output is prose; the
  `edge-case-hunter` layer prompt (JSON findings array, `location` = `file:line`) is the
  measurable unit first.
- Replacing `bmad-review` / `bmad-code-review` — they are the systems under test.
- Any dashboard, hosted service, or automatic prompt repair.

## Success signal

`eval-quality-smoke` exits 0 on the shipped corpus; the pilot contract compiles; a one-trial
twin-run preflights both arms and the mutated arm cites `pkg/discount.py:17` while the clean arm
does not; three trials per arm produce a catch rate the fleet can read — a number, not a feeling,
about the reviewer every unattended landing depends on.
