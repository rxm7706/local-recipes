---
spec: bmad-eval-quality
status: shipped
owner-dream: docs/dreams/bmad-eval-quality.md
surface:
  - recipes/bmad-eval-quality/**   # CAP-1 lands in the same PR as this Spec
  - evals/review-catches-planted-defect/**   # CAP-2 landed Story 45.2 (2026-09-07)
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
updated: "2026-09-09"
open_questions: []
  # ANSWERED 2026-09-09 (batch rows stA-C3 and stA-B1) — all three, in code:
  # 1. Driver env / reference model: the local-recipes pixi env (`pixi.toml:1044-1055`), with
  #    `evals/review-catches-planted-defect/driver.py:52-79` resolving `[adapter.review].model`
  #    through Marshal's own chain.
  # 2. Trial cost: a LOCAL LEDGER UNDER `evals/`, now — `driver.py:198` already reads
  #    `total_cost_usd` out of the `claude -p` envelope and `--max-budget-usd` bounds each run,
  #    while Story 44.15 is `blocked` behind the whole cutover. Fold into 44.15 metering only if
  #    that story ever ships. This Spec is the SINGLE OWNER of the question; the verbatim
  #    duplicate on `spec-bmad-suite-lifecycle` is deleted and cites this one.
  # 3. Daily-use env: local-recipes (`pixi.toml:1611`), the default env; `bmad-suite-full` is not
  #    the daily-use carrier.
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
  the tagged binary that has `score`. *Success:* `recipe-build` green; `eval-quality --version`
  prints the **pinned TAG version** (`1.4.1` today — `recipes/bmad-eval-quality/recipe.yaml:5,:35`),
  `--help` lists `score`, `compile` on a shipped corpus contract exits
  0; enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml` (auto-flows to metapackage
  run deps, doctor's drift watch, steward's pipeline-truth); pixi pin `bmad-eval-quality
  >=1.4.1` (`pixi.toml:1611`) with `environment.yaml` regenerated; baseline pin set, install-matrix,
  install-class and `library-llms-full.md` rows present; the PR carries `maintenance`.
- **CAP-2 — Pilot contract `review-catches-planted-defect`.** *Intent:* one Behavioral
  Evaluation Contract, run twin-arm (clean vs one planted `file:line` defect) against the
  `edge-case-hunter` review layer bmad-loop relies on, yields a catch rate the fleet can read.
  *Success:* the contract compiles; a one-trial twin-run preflights both arms, the mutated arm's
  review cites `pkg/discount.py:17` and the clean arm does not; three trials per arm yield a
  policy-comparable strength vector with a catch rate; pixi tasks `eval-quality-smoke`,
  `eval-quality-review-twin-run -- --trials N`, `eval-quality-review-replay` exist and are never
  wired into `detectors`. *Known limitation (empirical, live `--trials 3` runs):* the clean arm is
  a reproducible false-positive source — `edge-case-hunter`'s exhaustive-enumeration methodology
  finds a different real boundary concern at the same line every time; see `.memlog.md` for detail.

## Constraints

- Dream-first and the CFE rules bind: the recipe goes through `conda-forge-expert` (Rule 1); the
  effort closes with a CFE retro (Rule 2).
- **Tag-mode since 1.3.0** *(2026-09-09; the original `0.2.0.dev0 @ 3172162fbd…` commit pin is
  retired to historical record once upstream shipped v0.2.0..v1.4.1)*. Pin an **exact tag**, never
  a floating HEAD. **CFE G109 binds:** re-derive the version of record from the default branch on
  every bump — never assume the awaited tag. A schema mismatch fails `compile` loudly, never
  papered over.
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

## Currency — 2026-09-09

**Version of record: 1.4.1, published, both noarch variants.** The recipe moved
`0.2.0.dev0 @ 3172162fbd` → **1.3.0** (tag-mode; the awaited `v0.2.0` was five releases stale, CFE
G109) → **1.4.0** → **1.4.1** in one day. The 1.4.0→1.4.1 step is a live G109 recurrence and the
sharpest case for the rule: upstream cut v1.4.1 at 12:15Z *while this recipe was being updated to
v1.4.0* — the version of record moved mid-task, so a tag named in a request is never authority.
G110 re-read across every bump: the bin map (`eval-quality → dist/cli/main.js`), `files`,
`engines.node >=22.20.0` and the single `zod` prod dep never moved, so `build.sh` / `build.bat`
stayed untouched, the `Apache-2.0 AND MIT` expression and both `license_file` entries stayed
correct, and `build.number` stayed 0 (G113 — version moved).

Both variants are **confirmed in the SERVED repodata** (G66, not merely the file API): `__unix`
`h07402fc_0` built on a macos-14 runner, `__win` `h2fd06db_0` on windows-2022. `steward suite
pipeline-truth` reports `drifts: -` for this member — upstream, recipe, channel and installed all
read 1.4.1.

**Owner Dream flips `specified → realized`** (batch Class B row stA): CAP-1 and CAP-2 are both
exercised — recipe + channel + pixi pin, and `evals/review-catches-planted-defect/` with three pixi
tasks and live `--trials 3` twin runs. `specified` understated the gate. **This Spec stays
`shipped`**; only its version text moved. Read literally before this pass, the shipped recipe
failed its own Spec (batch row stA-D4) — that is what the CAP-1 and Constraints re-texts above fix.
