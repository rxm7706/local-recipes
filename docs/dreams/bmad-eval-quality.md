---
title: bmad-eval-quality — prove the reviewer catches the planted bug
type: dream
owner: steward
status: specified
---

# bmad-eval-quality — prove the reviewer catches the planted bug

## The Dream

The factory runs unattended. Every story that lands through a bmad-loop run passes exactly one
safety net: the independent reviewer, because `gate_mode = "none"` switched the human approval
gate off and left the reviewer as the last line. Nothing measures whether that reviewer would
actually catch a real defect. Every other quality surface in the repo is either deterministic (the
~30 `*-check` detectors, pyforge-doctor's sources, the CFE meta tests) or an LLM review whose
strength has never been proven. The repo's own memory records the failure class: detectors that
fail open when GitHub rate-limits them, a false-fact `[reject]` that hides a finding forever, a
fork that ignored review scope.

`eval-quality` ([bmad-code-org/bmad-eval-quality](https://github.com/bmad-code-org/bmad-eval-quality))
is the tool for that gap. It compiles and scores *Behavioral Evaluation Contracts* — versioned JSON
declaring which behaviors to probe, what evidence counts, and the pass/fail oracles — and its one
idea is the **twin-run loop**: run the same contract against a clean system and against one with a
single planted defect; a strong contract passes clean and fails mutated. It executes nothing
itself. Our harness runs the system under test and hands over observations and a sealed run
record; the tool grades the *evaluation*, not the system.

The dream: `bmad-eval-quality` is the fourteenth member of the bmad-suite, installed the suite's
way, and a first contract proves — with a planted `file:line` defect and a catch rate, not a
feeling — that the review layer bmad-loop relies on actually looks.

## Grounding — verified state (2026-09-05 research pass)

Upstream (checked against the tagged and main sources, not memory):

- npm `latest` is 0.1.0 (2026-08-28), the only git tag (`v0.1.0` = `65c6b808`; npm's `gitHead` is
  that same commit). It ships `compile`, `seal`, `preflight` — **no `score`**.
- Scoring (`score`, `runScore`, the `ingest` stage) and nine breaking schema-version bumps sit on
  unreleased main: package.json 0.2.0, HEAD `3172162fbdc7c4bb70ed11c1367dc3e433797535`
  (2026-09-04, the commit wiring the publish action). No runtime version checking — exact pinning
  required.
- `schemas/eval-contract.schema.json`: `permittedInterfaces[].kind` admits api/web/cli/mcp but
  "v0 supports `api`; the other three fail compilation". The shipped `examples/bmad-tea-contract.json`
  (kind cli, 7 of 21 fields) is illustrative and will not compile. Every contract models its SUT as
  an HTTP-shaped operation; the driver is the adapter.
- A contract has 21 required top-level fields; `corpus/dev/contracts/satisfied-declarations.json`
  is the canonical complete example.
- TypeScript with `dist/` gitignored; `prepack` runs `clean && build` (`tsc -p tsconfig-build.json`).
  Node ≥22.20, one prod dep (`zod`), Apache-2.0.
- TEA (`bmad-method-test-architecture-enterprise`) is the reference authoring client; eval-quality
  knows nothing about BMad. TEA is pinned in this repo's pixi but not installed as a module.

In-repo:

- No `evals/` directory and no skill-eval harness exists anywhere; `claude plugin eval` is
  referenced nowhere.
- bmad-loop's review session is `/bmad-build-auto` re-invoked on a `done` spec
  (`bmad_loop/engine.py`), routed to `step-04-review.md`; its findings are prose. The only
  JSON-emitting reviewer surface is the layer prompt
  `.claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md` ("Return ONLY a valid JSON
  array", `location` = `file:line`), byte-identical to the `bmad-code-review` copy.
- Suite membership is single-sourced at `recipes/bmad-suite/suite-members.yaml` (13 active); it
  feeds the metapackage run deps, pyforge-doctor's watched set (`_SUITE_PREFIX = "bmad-"` and
  `_manifest_suite_members`), and steward's pipeline-truth check. 12 of 13 members source from
  GitHub archives; six are commit-pinned with the `X.Y.Z.dev0 @ <sha>` encoding (G109).
- `tests/packaging/test_bmad_suite_full_feature.py:31-43` freezes the `bmad*` pin set as a
  metapackage-story guard against accidental pins.
- pixi already carries `nodejs >=24.19`; Node is not a blocker.

## Decisions locked (operator, 2026-09-05)

- **Conda name `bmad-eval-quality`.** Suite members carry the `bmad-` prefix after the upstream
  repo name even when the registry name lacks it (`bmad-labs-skills` ↔ `bmad-labs/skills`). The
  bin stays `eval-quality`. The frozen pin baseline gets the new name in the same PR; it is a
  guard, not a naming rule.
- **Source = GitHub main, commit-pinned `0.2.0.dev0 @ 3172162f`.** Rejected: npm 0.1.0 and tag
  v0.1.0 (same commit, no `score`, schema v1 already superseded — every contract authored against
  it would be rewritten at 0.2.0 anyway). The commit pin cannot move; a schema mismatch fails
  `compile` loudly. Flip to tag-mode the day `v0.2.0` lands (`0.1.0 < 0.2.0.dev0 < 0.2.0`).

## What it looks like when real

**Suite membership (CAP-1).** `recipes/bmad-eval-quality/recipe.yaml` in the labs-skills /
manticore encoding (`context.version: "0.2.0.dev0"`, `context.commit`, source = the commit
archive), built through `conda-forge-expert`: `npm ci` → `npm pack` (the tarball is named from
package.json, `eval-quality-0.2.0.tgz`, not from the conda version) → `npm install -g` →
`pnpm-licenses`; per-arch, `nodejs >=22.20.0` floor only. Tests prove the decision held:
`eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `compile` on the shipped
corpus example exits 0. One line in `suite-members.yaml` auto-enrolls it in the metapackage,
doctor's drift watch, and steward's pipeline-truth; the pixi pin
`bmad-eval-quality = ">=0.2.0.dev0"`, the baseline set extended, an install-matrix row with its
hazards, steward's install-class tables and `library-llms-full.md` each gaining a row,
`environment.yaml` regenerated, the `maintenance` label on the PR. Published to SelfExplainML
through the existing channel pipeline.

**The pilot contract (CAP-2).** `evals/review-catches-planted-defect/` holds a tiny fixture
package, `arms/clean.diff` and `arms/mutated.diff` (one boundary flip, e.g. `>=` → `>` at
`pkg/discount.py:17`), the contract with interface `review-api` / operation `review-diff`
(kind `api`), probes, scoring policy, isolation manifest, evaluator configuration, a findings JSON
schema, and a ~150-line `subprocess`-only driver. The driver runs the `edge-case-hunter` layer
headlessly (`claude -p --output-format json --json-schema … --max-budget-usd 2
--no-session-persistence`, model pinned to the station's `[adapter.review].model`), maps exit
code + parsed findings to an observation, and emits the sealed run record. One strong oracle:
`covers-by-key` over `referenceSets.planted-defects` (`["file","line"]`) against the review's
cited locations — "the review ran" never passes on its own. Pixi tasks `eval-quality-smoke`,
`eval-quality-review-twin-run -- --trials N`, `eval-quality-review-replay`; never wired into
`detectors`, because this measures the reviewer and is not a PR gate.

**Success signal.** Smoke exits 0 on the shipped corpus; the pilot contract compiles; a one-trial
twin-run preflights both arms and the mutated arm cites `pkg/discount.py:17` while the clean arm
does not; three trials per arm yield a policy-comparable strength vector with a catch rate the
fleet can read.

## What is real

Nothing in the repo yet. The assessment and plan exist (2026-09-05); this Dream is their seed.
Dream-first applies: `bmad-spec` under `pyforge-steward` produces the contract before any recipe
or driver code.

## Constraints

- Dream-first and the CFE rules: the recipe goes through `conda-forge-expert` (Rule 1) and the
  effort ends with a CFE retro (Rule 2).
- Exact commit pin; bump `version` and `commit` together; never a floating HEAD.
- The pilot is not a gate. Findings stay measurements of the reviewer; Warden remains the sole PR
  verdict.
- Cost is bounded per run (`--max-budget-usd`); report catch-rate across trials, never one
  verdict, and pin model + effort.
- `spec-bmad-suite-channel-product` § Non-goals ("packaging anything new") is deliberately
  overridden for this fourteenth member.

## Non-goals

- Installing TEA as a module (it stays a pinned suite member; TEA is not needed to author
  contracts).
- Evaluating the full `bmad-build-auto` review skill end-to-end (no JSON surface; the layer
  prompt is the measurable unit first).
- Replacing `bmad-review` / `bmad-code-review` — they are the systems under test.
- Any dashboard, hosted service, or automatic prompt repair (upstream's own out-of-scope list).

## Kinships

- [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md) /
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md) — the membership machinery this joins.
- [`bmad-module-provisioning.md`](bmad-module-provisioning.md) — install-class wiring precedent.
- [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) — sibling question about the
  reviewer; this Dream supplies the measurement that one would need.

## Realization log

- **2026-09-05** — Seeded from the assessment of
  [bmad-code-org/bmad-eval-quality](https://github.com/bmad-code-org/bmad-eval-quality). Operator
  locked the conda name (`bmad-eval-quality`) and the source (main, commit-pinned
  `0.2.0.dev0 @ 3172162f`). Next: `bmad-spec` under pyforge-steward.
- **2026-09-05 (later)** — `bmad-spec` derived `spec-bmad-eval-quality` under pyforge-steward
  (SPEC.md + `packaging.md` + `pilot-contract.md`; CAP-1 suite membership, CAP-2 pilot contract;
  status `ready`). Grounding re-verified same day: HEAD still `3172162f`, only `v0.1.0` tagged, npm
  0.1.0. CAP-1 is being built in the same PR as the Spec, in the SelfExplainML packaging pass that
  also retires `bmad-method-wds-expansion` (deprecated in the 6.12.0 core module registry; `bmad-ux`
  absorbs it) — the suite stays at 13 active members.
