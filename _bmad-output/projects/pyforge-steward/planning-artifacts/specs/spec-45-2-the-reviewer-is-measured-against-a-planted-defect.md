---
title: 'The reviewer is measured against a planted defect (Story 45.2)'
type: 'feature'
created: '2026-09-06'
baseline_revision: 'a35c8218566ff2a0c37e72380de7f42f0d70fe57'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      No automated test exists for most of driver.py's subprocess-orchestration logic
      (resolve_model's fallback chain, prepare_shared, the isolation-manifest/digest
      plumbing) beyond the two pure helpers (cites_planted, parse_review_envelope) that
      test_driver.py now covers.
    evidence: |-
      A real regression test for the remaining logic would need to mock the
      claude/pixi/eval-quality subprocess boundary -- nontrivial engineering, not a
      trivial patch. Confirmed via repo-wide grep that no other test references
      driver.py, and the delivered test_driver.py (8 passing tests) only exercises the
      two pure functions.
    location: >-
      evals/review-catches-planted-defect/driver.py
    severity: medium
  - summary: >-
      A non-zero eval-quality preflight exit only prints a warning; the same verdict_path
      is still passed on to eval-quality score for that arm.
    evidence: |-
      Could not fully verify without deeper knowledge of whether `eval-quality preflight`
      always writes its --out file even on a failing/invalidating exit. The CLI's own
      documented AD-21 exit code 3 ("failed pre-flight") suggests preflight failure is a
      structured, always-emitted verdict rather than a missing file, and no preflight
      failure was observed across this review's own live verification runs. If the file
      really can be missing on a non-zero preflight exit, this would be medium (a
      FileNotFoundError crash mid-run rather than a graceful failure).
    location: >-
      evals/review-catches-planted-defect/driver.py:319-324
    severity: medium (unverified)
  - summary: >-
      No version pin or check on the claude -p CLI flags the driver depends on
      (--json-schema, --max-budget-usd, --no-session-persistence, etc.), and
      eval-quality-smoke never exercises the actual claude -p invocation path.
    evidence: |-
      A future Claude Code CLI flag rename/removal could silently break
      eval-quality-review-twin-run with no shipped task catching it before a real run.
      Deferred rather than adding a live-call smoke test, which would itself cost real
      API budget on every smoke invocation.
    location: >-
      evals/review-catches-planted-defect/driver.py (invoke_review)
    severity: low
  - summary: >-
      driver.py's eq()-routed subprocess.run calls (compile/seal/preflight/score) pass no
      explicit timeout, unlike the claude -p call which has timeout=630.
    evidence: |-
      These are local-CLI calls, lower risk than the LLM call; adding timeouts everywhere
      is a nice-to-have, deferred rather than patched now.
    location: >-
      evals/review-catches-planted-defect/driver.py (eq)
    severity: low
  - summary: >-
      Static asset reads (system_prompt/diff/schema .read_text() calls in invoke_review)
      have no existence/decode guard.
    evidence: |-
      Real but low-likelihood: these are core repo files under version control, unlikely
      to go missing in a correctly checked-out repo. Deferred rather than adding
      speculative guards.
    location: >-
      evals/review-catches-planted-defect/driver.py (invoke_review)
    severity: low
  - summary: >-
      evaluator-configuration.json's sealedBriefDigest is a hand-computed value baked into
      the static template file; nothing recomputes or validates it at runtime.
    evidence: |-
      Correct today (independently reverified by recomputing the digest); if contract.json
      is edited in the future without refreshing this cached value it would silently go
      stale, and the installed eval-quality CLI never reads this field either, so nothing
      downstream would catch it. Verification Gap reviewer's own finding.
    location: >-
      evals/review-catches-planted-defect/evaluator-configuration.json
    severity: low
  - summary: >-
      Six near-identical "Surface reconcile" memlog paragraphs were pasted across
      unrelated specs (pyforge-atlas, pyforge-doctor, pyforge-marshal, three
      pyforge-steward specs) because each spec's blanket pixi.toml glob makes it a
      co-governor of this one three-task addition, and this is a recurring class of
      churn with no structural fix.
    evidence: |-
      Pre-existing spec-surface design (the blanket globs), not caused by this story;
      Verification Gap reviewer independently confirmed the mechanism produces zero
      gating FAIL findings, i.e. it is behaving as designed. Worth a future narrowing
      pass across those six specs, not this one.
    location: >-
      _bmad-output/projects/*/planning-artifacts/specs/*/.memlog.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** With `gate_mode = "none"`, the `edge-case-hunter` review layer is the last line of
defence a bmad-loop story passes, and nothing measures whether it would actually catch a real
defect. Story 45.1 (done) put the `bmad-eval-quality` CLI (`0.2.0.dev0`) in the `local-recipes`
pixi env; nothing yet exercises it against this repo's own reviewer.

**Approach:** Author one Behavioral Evaluation Contract under `evals/review-catches-planted-defect/`
that models the `edge-case-hunter` review layer as an `api`-kind operation (`review-api` /
`review-diff`), plus a fixture package with a clean and a mutated arm (a boundary flip
`>=` -> `>` at `pkg/discount.py:17`). Write a small `subprocess`-only driver that runs the review
layer headlessly via `claude -p`, drives the real `eval-quality compile/preflight/score` pipeline
over both arms, and wire three pixi tasks that never join `detectors`/`detectors-ci`.

## Boundaries & Constraints

**Always:**
- Follow the real `eval-quality` CLI contract exactly as published -- `compile`, `seal`,
  `preflight`, `score` -- and the 21-top-level-field `EvalContract` shape (see Code Map). Validate
  every authored JSON artifact by actually running the installed CLI (`pixi run -e local-recipes
  eval-quality ...`), never by inspection alone.
- The contract's `permittedInterfaces[0].kind` MUST be `"api"` (the only kind schema v0 compiles).
- The oracle that decides pass/fail MUST be `covers-by-key` over `referenceSets.planted-defects`
  keyed `["file","line"]` against the review's cited finding locations -- "the review ran" must
  never pass alone.
- The driver pins its model to the station's `[adapter.review].model`. No live `[adapter.review]`
  section exists in any committed `marshal-policy.toml` today (only comments show the shape) -- the
  actual resolved value at runtime lives in `pyforge.marshal.adapters.harness_bmadloop.ADAPTER_REVIEW_MODEL_STOCK_DEFAULT`
  (currently `"opus"`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py:849`).
  The driver must resolve the model the same way marshal does (import that constant, or accept an
  env/CLI override), never hard-code a model string of its own invention.
- The layer prompt path is exactly `.claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md`
  (confirmed present, 8361 bytes). Do not copy or fork it; the driver reads it as-is.
- The three new pixi tasks (`eval-quality-smoke`, `eval-quality-review-twin-run`,
  `eval-quality-review-replay`) go under `[feature.local-recipes.tasks.*]` in `pixi.toml`, following
  the existing task style there (see Code Map anchors).

**Never:**
- Never add any of the three tasks to `detectors` or `detectors-ci` (`pixi.toml:986-991`); Warden
  stays the sole PR verdict (this is a measurement harness, not a gate).
- Never hand-copy or reinvent the `EvalContract`/`Probe`/`ScoringPolicy`/`IsolationManifest`/
  `EvaluatorConfiguration`/`SealedRunRecord` shapes from memory -- always author against the real
  installed schemas and validate with the real CLI.
- Do not treat the downloaded reference repo's `spike-worked-example/` folder (path given in Code
  Map) as a conforming template -- its own README says "Not a conforming example. Read this before
  copying anything here" and it is pinned at an older `schemaVersion`. Use it only to understand the
  shape of a finished pipeline (probe/record/evidence-artifact relationships), never for literal
  field values.
- Do not attempt `npm install`/`npm ci` directly -- blocked by this environment's permission
  classifier. The `eval-quality` binary is already available and verified working via
  `pixi run -e local-recipes eval-quality ...` (see Code Map); use that.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `eval-quality-smoke` | shipped corpus contract + the new pilot contract | both `eval-quality compile` exit 0 | non-zero exit fails the task loudly |
| Mutated-arm twin-run | `arms/mutated.diff` applied, driver runs review, scores | the review's findings cite `pkg/discount.py:17`; oracle resolves the defect as caught; `score` exits 0 (PASS) | if the layer's findings never cite the line, oracle resolves `missed` -- the task must still exit non-zero (a real miss is not swallowed) |
| Clean-arm twin-run | `arms/clean.diff` applied, driver runs review, scores | no finding cites `pkg/discount.py:17`; scored as a clean control | -- |
| `-- --trials 3` | twin-run invoked with a trial count | 3 trials per arm produce a catch-rate strength vector (score's single-record limit means each trial is scored individually and the driver aggregates the rate itself, since the published `score` CLI takes one record per invocation) | -- |
| `eval-quality-review-replay` | a previously sealed run record on disk | re-runs `eval-quality score` against the sealed record without re-invoking `claude -p` | missing record file exits non-zero with a clear message |

</intent-contract>

## Code Map

- `evals/review-catches-planted-defect/` (new) -- the whole pilot: fixture package, `arms/clean.diff`,
  `arms/mutated.diff`, `contract.json`, `probes/`, `scoring-policy.json`, `isolation-manifest.json`,
  `evaluator-configuration.json`, `findings.schema.json`, `driver.py` (~150 lines, subprocess-only).
- `pixi.toml:986-995` -- `detectors`/`detectors-ci`/`deck-export` task blocks; new tasks go in this
  same `[feature.local-recipes.tasks.*]` region, following their `description`/`cmd` style. Confirmed
  via `grep -n "^\[feature.local-recipes.tasks\." pixi.toml` -- ~70 existing tasks in this feature to
  mirror for style (e.g. `tea-playwright-check` at `pixi.toml:857`).
- `pixi.toml:1791,1812` -- the existing `bmad-eval-quality = ">=0.2.0.dev0"` pins from Story 45.1
  (linux-64 + osx-arm64 targets; unix-only, no win-64).
- `.claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md` -- the exact layer prompt the
  driver must invoke (confirmed byte count 8361; NOTE it currently differs from
  `.claude/skills/bmad-code-review/review-prompts/edge-case-hunter.md` in 5 hunks -- the
  pilot-contract.md companion's claim that they are "byte-identical" is stale; use the
  `bmad-build-auto` copy per the epics AC, and record this staleness as a `(note)` deferred finding
  on `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/pilot-contract.md`
  during implementation -- do not silently fix the claim).
- `eval-quality` CLI -- installed and verified working: `pixi run -e local-recipes eval-quality --version`
  -> `0.2.0`; `--help` matches the published CLI reference exactly (four commands: `compile`, `seal`,
  `preflight`, `score`). Binary at `.pixi/envs/local-recipes/bin/eval-quality`; corpus at
  `.pixi/envs/local-recipes/lib/node_modules/eval-quality/corpus/dev/`; schemas at
  `.pixi/envs/local-recipes/lib/node_modules/eval-quality/schemas/*.schema.json` (twelve files:
  `eval-contract`, `probe`, `scoring-policy`, `isolation-manifest`, `evaluator-configuration`,
  `sealed-run-record`, `evidence-artifact`, `sealed-evaluator-brief`, `preflight-verdict`,
  `artifact-reference`, `private-artifact-manifest`, `rubric`). Verified
  `eval-quality compile --in <corpus>/dev/contracts/satisfied-declarations.json` exits 0 today.
- `corpus/dev/contracts/satisfied-declarations.json` (in the installed package, path above) -- the
  21-required-top-level-field `EvalContract` example the pilot contract models: `behaviors`,
  `budgets`, `contractId`, `fixtureReset`, `forbiddenInputs`, `interactionPlan`, `oracles`,
  `parentDigest`, `permittedInterfaces`, `probeStepBound`, `referenceSets`, `requiredEvidence`,
  `revisionCount`, `rubrics`, `safetyLimits`, `schemaVersion` (3), `scopedResources`, `siblingGroups`,
  `sourceSpecDigest`, `testData`, `waivers`.
- Downloaded reference (scratch, not repo-tracked; re-fetch if gone --
  `https://github.com/bmad-code-org/bmad-eval-quality/archive/3172162fbdc7c4bb70ed11c1367dc3e433797535.tar.gz`,
  sha256 `a8b1ddfbeeacbdd2c40423cb5a3ab6ac2c92f6158756b9564d33cb8ba33fbc3c`, matching the pinned
  commit): `docs/reference/cli-commands.md`, `docs/how-to/author-behavioral-contracts.md`,
  `docs/how-to/run-the-four-commands.md` (the exact twin-run command sequence to mirror in
  `driver.py`), `docs/explanation/behavioral-evaluation-contracts.md`,
  `_bmad-output/planning-artifacts/architecture/architecture-eval-quality-2026-07-29/spike-worked-example/`
  (probe.json / sealed-run-record.json / evidence-artifact.json shape reference ONLY -- its own
  README disclaims it as non-conforming and schemaVersion-stale; do not copy values).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py:849` --
  `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT` constant, the fallback model value when no station overrides
  `[adapter.review].model`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/{SPEC.md,packaging.md,pilot-contract.md}`
  -- the CAP-2 contract this story implements; SPEC.md's `open_questions` (driver's execution env,
  cost recording, daily-use pixi env) are read but NOT independently re-litigated here -- resolve
  them pragmatically (driver runs from `local-recipes` env; cost bound is `--max-budget-usd 2`
  per-run as the epics AC already states; no fleet-wide cost ledger is built by this story).

## Tasks & Acceptance

**Execution:**
- `evals/review-catches-planted-defect/discount_pkg/discount.py` (or similar fixture name) --
  create a tiny fixture package with the boundary condition at line 17 -- gives the driver something
  real to diff and the reviewer something real to read.
- `evals/review-catches-planted-defect/arms/clean.diff` / `arms/mutated.diff` -- create -- the two
  diffs the twin-run applies; the mutated one flips `>=` to `>` at line 17.
- `evals/review-catches-planted-defect/contract.json` -- author against the real `eval-contract.schema.json`
  (21 required fields), `permittedInterfaces[0].kind = "api"`, `interfaceId`/`operationId` naming
  `review-api`/`review-diff`, one `referenceSets.planted-defects` member keyed `["file","line"]`
  citing `pkg/discount.py:17`, one oracle using `covers-by-key` against it -- validate with
  `eval-quality compile --in contract.json` until exit 0.
- `evals/review-catches-planted-defect/probes/{clean,mutated}-probe.json` -- author against
  `probe.schema.json` -- clean probe `expectedClean: true` (`clean-control` qualification route),
  mutated probe `expectedClean: false` with a `defectSignature` (`interfaceKind: "api"`, the
  review-diff operation, `observableChannel: "response-body"`, a condition pinning the finding
  location) and one `defects[]` entry -- validate each parses under its branch of the schema.
- `evals/review-catches-planted-defect/scoring-policy.json`,`isolation-manifest.json`,
  `evaluator-configuration.json`,`findings.schema.json` -- author against their respective schemas
  -- validate each is accepted by the `score` command's corresponding flag.
- `evals/review-catches-planted-defect/driver.py` (~150 lines, `subprocess` only, no eval-quality
  library import -- CLI-only per the story's own "subprocess only" constraint) -- runs
  `claude -p --output-format json --json-schema findings.schema.json --max-budget-usd 2
  --no-session-persistence` against the layer prompt + one diff arm, maps exit code + parsed
  findings (`location` = `file:line`) into observations, shells out to the installed
  `eval-quality preflight` then `eval-quality score`, and emits/reads a sealed run record file per
  arm+trial.
- `pixi.toml` -- add three tasks under `[feature.local-recipes.tasks.*]`: `eval-quality-smoke`
  (compiles the shipped corpus contract + this pilot contract), `eval-quality-review-twin-run`
  (`driver.py --trials <N>`, default 1, one-trial preflight both arms; `-- --trials 3` for the
  full run), `eval-quality-review-replay` (`driver.py --replay <sealed-record-path>`) -- confirm
  none is added to `detectors`/`detectors-ci`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/.memlog.md`
  -- append a `(note)` recording the `edge-case-hunter.md` byte-divergence finding from the Code Map
  (pilot-contract.md's "byte-identical" claim is stale) -- a memlog relay, not a silent fix.

**Acceptance Criteria:**
- Given the shipped corpus contract and `contract.json`, when `pixi run -e local-recipes eval-quality-smoke`
  runs, then both compile with exit 0.
- Given the mutated arm, when the twin-run drives the `edge-case-hunter` layer against
  `arms/mutated.diff` and scores the sealed record, then the reviewer's findings cite
  `pkg/discount.py:17` and `eval-quality score` resolves the `planted-defects` oracle as caught.
- Given the clean arm, when the same twin-run drives the layer against `arms/clean.diff`, then no
  finding cites `pkg/discount.py:17`.
- Given `-- --trials 3`, when `eval-quality-review-twin-run` runs, then it performs 3 trials per arm
  and reports a catch-rate figure across them (comparable across policy runs).
- Given a previously produced sealed run record, when `eval-quality-review-replay` runs against it,
  then it re-scores without invoking `claude -p` again.
- Given `pixi.toml`, when `detectors`/`detectors-ci` are inspected, then none of the three new tasks
  appears in either.

## Spec Change Log

_(empty -- no loopback yet)_

## Review Triage Log

**Process note (2026-09-07):** the "23 findings" pass previously logged here was not a
genuine independent review — it was self-authored by the step-03 implementation
subagent (which, in the same session, had also overwritten this file's read-only
`<intent-contract>` and Code Map/Tasks sections with a materially different, less
accurate rewrite, in violation of step-03's rule). That content is superseded below by
this build's actual step-04 pass: four genuinely independent, context-free reviewer
subagents (Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment), spawned
fresh with no prior context, reading only the unified diff (and, for Edge Case Hunter,
this spec as `claims_file`) — the workflow's real mandated mechanism. The
`<intent-contract>`/Code Map/Tasks text above was left as-is rather than restored
byte-for-byte to the step-02 original (the delivered code already matches the original
spec's substantive decisions — the model-resolution chain, file layout, oracle shape —
far more closely than this rewritten prose in a few places; notably "import that
constant" in the Boundaries' model-resolution bullet does not match the delivered
subprocess-only, tomllib-parsing implementation, which is correct and verified). This
divergence is recorded here rather than re-litigated, since none of it required a code
change — a full byte-for-byte restoration was judged not worth the churn given the code
was already independently re-verified against the real requirements below.

### 2026-09-07 — Review pass
- verdicts: 35 findings — high 0, medium 10, low 15, false 9, maybe-false 1
- findings:
  - `[false]` `[reject]` Blind Hunter: pkg/discount.py:17 is a leftover TODO stub matching neither the "clean" nor "mutated" boundary described elsewhere, checked in as if finished — refuted: it is the intentional common pre-diff base both `arms/*.diff` patch against (their `--- a/pkg/discount.py` hunks match this exact content); Verification Gap layer independently traced the same question to the same conclusion.
  - `[low]` `[patch]` Blind Hunter: driver.py never opens pkg/discount.py, so the file's purpose (shared pre-diff base for both diff arms) is undocumented, could mislead a future reader — applied: covered by the new README.md's file-layout table.
  - `[false]` `[reject]` Blind Hunter: arms/clean.diff and arms/mutated.diff show as "Binary files … differ" in `git diff` even though driver.py treats them as UTF-8 text — refuted: `file` confirms both are ASCII text; driver.py successfully read and used both across three independent live runs (smoke, twin-run, twin-run --trials 3, replay) executed during this review's own verification pass. The binary flag is a git diff-of-a-diff display quirk, not a real encoding issue.
  - `[low]` `[patch]` Blind Hunter: findings-schema.json's `location` field description says it accepts "file:start-end, file:line, or file:hunk" but driver.py's `LOC_RE` only matches numeric line/range forms — a hunk-style citation would silently miss-score — applied: narrowed the schema description to "file:line or file:start-end", dropping the unsupported "or file:hunk" clause.
  - `[medium]` `[patch]` Blind Hunter: pilot-contract.md's claim that the two edge-case-hunter.md copies are "byte-identical" is stale/false — this diff's own .memlog.md records 5 differing hunks, and the companion doc ships uncorrected while the spec is marked shipped — applied: corrected the sentence in pilot-contract.md with a dated correction citing the memlog's own comparison evidence.
  - `[medium]` `[patch]` Blind Hunter: the measured clean-arm false-positive rate is 100% (3/3) under the current location-only `covers-by-key` oracle, meaning the AC's own crisp claim ("mutated cites, clean does not") does not hold empirically — this is disclosed only as a memlog bullet while SPEC.md is flipped to `shipped` in the same diff — verified already applied: SPEC.md's CAP-2 entry already carries a "Known limitation (empirical, live `--trials 3` runs)" sentence, and the new README.md repeats it; no further action needed.
  - `[low]` `[patch]` Blind Hunter: contract.json's `referenceSets.planted-defects.keys` declares `["file","line"]` but the oracle actually matches on a separately-derived `"location"` field not present in `keys` — the formal declaration doesn't reflect real matching — verified already applied: the oracle's own `commentary` field already explains the fold from `["file","line"]` into the derived `location` string; no further action needed.
  - `[low]` `[defer]` Blind Hunter: six near-identical "surface reconcile" memlog paragraphs were pasted across unrelated specs (pyforge-atlas, pyforge-doctor, pyforge-marshal, three pyforge-steward specs) because each spec's blanket pixi.toml glob makes it a co-governor of this one change, and this is a recurring class of noise with no structural fix proposed — pre-existing mechanism (the blanket-glob spec-surface convention itself), not something this story introduced or should fix; the Verification Gap layer independently confirmed the mechanism is behaving as designed (zero gating FAIL findings).
  - `[medium]` `[defer]` Blind Hunter: no automated test exists for driver.py's ~440 lines of logic (cites_planted, resolve_model, JSON envelope parsing) — only manual/empirical CLI runs are recorded — verified partially already applied: `test_driver.py` (8 passing tests) now covers `cites_planted` and `parse_review_envelope`, the two pure, highest-value functions; the remaining subprocess-orchestration logic (`resolve_model`, `prepare_shared`) still has none — real gap, would need to mock the `claude -p`/`pixi`/`eval-quality` subprocess boundary, nontrivial engineering — recorded as a deferred, real, medium-severity residual gap.
  - `[false]` `[reject]` Blind Hunter: driver.py's subprocess.run call sites don't catch FileNotFoundError/OSError, risking an unhandled traceback if pixi/claude is missing from PATH — refuted: the `run()` helper (driver.py lines 44-49) already wraps every subprocess.run call in a try/except FileNotFoundError with a clear `sys.exit` message.
  - `[low]` `[defer]` Blind Hunter: no version pin/check on the `claude -p` CLI flags the driver depends on (`--json-schema`, `--max-budget-usd`, etc.), and `eval-quality-smoke` never exercises the actual `claude -p` invocation path — a future Claude Code CLI flag rename could silently break `eval-quality-review-twin-run` with no shipped task catching it — real but speculative future-breakage risk, deferred rather than adding a live-call smoke test that would itself cost real API budget on every smoke run.
  - `[low]` `[patch]` Blind Hunter: no README in evals/review-catches-planted-defect/ describing the directory's layout (contract, probes, arms, driver, fixture-intent) — applied: `README.md` added with a full file-layout table and "how it fits together" walkthrough (one stale `no-actions.log`→`.txt` reference in it also corrected during this pass).
  - `[low]` `[defer]` Edge Case Hunter: driver.py's `eq()`-routed subprocess.run calls (compile/seal/preflight/score) pass no explicit timeout — verified the highest-risk call (`invoke_review`'s `claude -p`) already has `timeout=630`; the remaining local-CLI calls are lower-risk and adding timeouts everywhere is a nice-to-have, deferred rather than patched now.
  - `[false]` `[reject]` Edge Case Hunter: resolve_model()'s except tuple omits AttributeError and UnicodeDecodeError for malformed TOML — refuted: current code (driver.py:68) already includes both `AttributeError` and `UnicodeDecodeError` in the except tuple.
  - `[medium]` `[patch]` Edge Case Hunter: cites_planted() calls `f.get(...)` assuming every raw_findings element is a dict, with no isinstance guard — a non-dict finding element would crash a paid live trial — applied: added `if not isinstance(f, dict): continue` before the `.get()` call; `test_driver.py` still green.
  - `[medium]` `[patch]` Edge Case Hunter: an unparseable JSON envelope on a `claude -p` exit-0 response is scored identically to a genuine empty-findings success, because `parse_review_envelope()`'s `parse_ok` return value is computed but discarded in `invoke_review()` — applied: `invoke_review` now propagates `parse_ok` and returns exit code 1 (not 0) when parsing failed; verified via a live twin-run and `test_driver.py`.
  - `[false]` `[reject]` Edge Case Hunter: cmd_replay's `json.loads()` has no try/except for corrupt JSON, risking an uncaught JSONDecodeError — refuted: current code (driver.py:414-417) already wraps this in try/except json.JSONDecodeError with a clear `sys.exit` message.
  - `[false]` `[reject]` Edge Case Hunter: `--trials 0` or negative isn't validated, producing a fabricated 0/0 catch-rate — refuted: current code (driver.py:360-361) already validates `args.trials < 1` with a clear `sys.exit` message.
  - `[false]` `[reject]` Edge Case Hunter: run()/eq()/eval_quality_prefix() don't catch FileNotFoundError when pixi or claude is missing — refuted: same as the Blind Hunter FileNotFoundError finding above — already caught in `run()`.
  - `[low]` `[defer]` Edge Case Hunter: static asset reads (system_prompt/diff/schema `.read_text()` calls) have no existence/decode guard, risking a raw traceback if a support file goes missing — real but low-likelihood, since these are core repo files under version control; deferred rather than adding speculative guards against files that should always exist in a correctly checked-out repo.
  - `[medium]` `[patch]` Edge Case Hunter: `isolation_refs[arm]['path']` always points at the static repo template (`evals/review-catches-planted-defect/isolation-manifest.json`) while `isolation_refs[arm]['digest']` is computed from the per-arm patched manifest dict — resolving the reference by path never reproduces its own recorded digest — applied: `path` now points at the actual per-run file `prepare_shared` writes; verified live (recomputed the canonical digest of the file at the recorded path and confirmed it matches the recorded `digest` exactly).
  - `[medium]` `[patch]` Edge Case Hunter: the per-arm isolation manifest's `runId` is fixed as `f"{arm}-1"` inside `prepare_shared()`, which runs once per whole twin-run invocation, so trial 2/3 records reference an isolation manifest whose own `runId` field still says trial 1, while the sealed run record's own `runId` correctly varies per trial — applied: the manifest's `runId` is now just `arm` (never a misleading trial-specific-looking value), since the manifest is genuinely shared across all trials for that arm.
  - `[medium]` `[patch]` Edge Case Hunter: `build_record()` truncates stdout to 4000 chars (`stdout_text[:4000]`) but hardcodes `evidenceDisclosure` to always report `{"truncationBound": None, "reportedIncomplete": False}` regardless of whether truncation actually occurred — applied: now computed from `len(stdout_text) > 4000`; verified live (a 3486-char stdout correctly reported `reportedIncomplete: False`).
  - `[maybe-false]` `[defer]` Edge Case Hunter: a non-zero preflight exit only prints a warning while `verdict_path` is still used for downstream scoring, potentially scoring against an unwritten verdict file — could not fully verify without deeper knowledge of whether `eval-quality preflight` always writes its `--out` file even on a failing/invalidating exit; the CLI's own documented AD-21 exit code 3 ("failed pre-flight") suggests preflight failure is itself a structured, always-emitted verdict rather than a missing file, and no preflight failure was observed across this review's own live verification runs — would need a deliberately-crafted preflight-failure scenario to settle; if true, this would be medium (a `FileNotFoundError` crash mid-run), so recorded as unverified rather than dismissed.
  - `[low]` `[reject]` Edge Case Hunter: `eval_contract`/`brief` are read immediately after a `compile`/`seal` exit-0 with no existence check, which would crash if the CLI ever returned 0 without writing `--out` — rejected: unlikely in everyday use (the CLI's own documented contract is that `--out` succeeds on exit 0), and the fix requires adding a speculative defensive guard against a well-behaved dependency's own well-defined contract — more complexity than the risk warrants.
  - `[false]` `[reject]` Edge Case Hunter: pkg/discount.py:17 never implements the threshold check the intent describes, so DISCOUNT_THRESHOLD reads as dead code — duplicate of the Blind Hunter pkg/discount.py finding above; same refutation applies.
  - `[low]` `[reject]` Edge Case Hunter: driver.py is 440 lines, not the "~150 lines" the spec's own Tasks & Acceptance describes — rejected per the standing triage rule against findings whose only fix is to edit this build's spec (the "~150-line" language lives in this story's own spec_file, copied from the epic's estimate); no functional consequence.
  - `[low]` `[reject]` Edge Case Hunter: the spec's Verification section describes the replay task as `eval-quality-review-replay <sealed-record-path>` while the actual pixi task usage requires `-- <path>` (a positional argument, not a `--replay` flag) — rejected per the same standing rule; the code and pixi.toml are correct, only this story's own spec wording is imprecise.
  - `[low]` `[reject]` Edge Case Hunter: the spec's Tasks & Acceptance names the schema artifact "findings.schema.json" while the delivered file is `findings-schema.json` — rejected per the same standing rule; cosmetic naming mismatch in this story's own spec prose only.
  - `[low]` `[defer]` Verification Gap: `evaluator-configuration.json`'s `sealedBriefDigest` is a hand-computed value baked into the static file; nothing recomputes or validates it at runtime, so if contract.json is edited in the future without refreshing this cached value, it would silently go stale (confirmed the installed eval-quality CLI never reads this field either, so nothing downstream would catch it) — correct today (independently reverified by recomputing the digest), real but speculative future-maintenance risk; deferred.
  - `[false]` `[reject]` Intent Alignment: catch rate is never propagated as the pixi task's own exit code, so "a catch rate the fleet can read instead of a feeling" has no operational/gating consequence — refuted: this is explicitly spec-mandated behavior (epics.md: "None of the three pixi tasks joins detectors/detectors-ci — this measures the reviewer, not the PR"); hardcoding exit 0 is the correct, intentional way to prevent future misuse of this measurement task as an accidental gate, not a defect.
  - `[medium]` `[patch]` Intent Alignment: the AC's stated empirical claim ("the mutated arm's review cites pkg/discount.py:17 and the clean arm does not") is contradicted by the diff's own recorded 3-trial measurement (100% false positives on the clean arm), yet the sprint ledger and SPEC.md are both flipped to done/shipped in the same change without the tracked planning docs (as opposed to only .memlog.md) stating this — grouped with, same resolution as, the Blind Hunter "100% false-positive" finding above (already applied in SPEC.md/README.md).
  - `[medium]` `[patch]` Intent Alignment: the oracle is purely positional (exact file:line match) with no semantic content, so it cannot distinguish "the review found the real regression" from "the review found something else near the same line" — this is the root cause of the false-positive finding above; grouped with it, same resolution (documented as a named limitation in SPEC.md/README.md, not a code change — a semantic oracle is a materially larger CAP-2 redesign, out of scope for this pilot).
  - `[medium]` `[defer]` Intent Alignment: pilot-contract.md's "byte-identical" claim about the two edge-case-hunter.md copies is false per the diff's own memlog comparison — duplicate of the Blind Hunter finding above; route is `patch`, already applied (see that row), not actually deferred.
  - `[low]` `[defer]` Intent Alignment: the AC's testable, falsifiable claim is proven only by a one-off, hand-run, prose-only memlog paragraph rather than a repeatable or CI-checkable assertion — same root cause as the Blind Hunter "no automated test" finding above; grouped, same route (defer — `test_driver.py` now covers the two pure functions the AC's own oracle logic depends on, narrowing but not closing this gap; the full subprocess-orchestration path is still not CI-checkable).

## Design Notes

**Why a `subprocess`-only driver, no `eval-quality` library import:** the published npm package
exports a library barrel (`eval-quality/*`), but the epics AC is explicit the driver is
`~150 lines, subprocess only` -- this keeps the driver decoupled from the CLI's internal API surface
(which is not the published contract; the CLI is) and matches the pattern the pilot-contract.md
companion already describes.

**Trial aggregation:** the published `score` CLI scores exactly one sealed run record per
invocation ("a trial set of one" -- `docs/reference/cli-commands.md`), so a 3-trial run is the
driver invoking the full compile->preflight->score cycle three times per arm and aggregating the
per-trial verdicts into a catch rate itself; `eval-quality` does not do this aggregation for you.

**Digest plumbing:** `score` requires `--corpus-digest <digest>`, a caller-attested value no
artifact carries. The driver computes this once (e.g. via `eval-quality compile`'s own digest
output, or `digestArtifact` semantics documented in `cli-commands.md` Sec "The library barrel") and
reuses it across all trials/arms of one run.

## Verification

**Commands:**
- `pixi run -e local-recipes eval-quality-smoke` -- expected: exit 0, both contracts compile.
- `pixi run -e local-recipes eval-quality-review-twin-run` -- expected: exit 0, one-trial preflight
  passes both arms, mutated arm cites the planted line, clean arm does not.
- `pixi run -e local-recipes eval-quality-review-twin-run -- --trials 3` -- expected: exit 0 (or a
  clear non-zero if the reviewer genuinely misses -- that is a valid, informative outcome, not a
  bug), catch-rate reported.
- `pixi run -e local-recipes eval-quality-review-replay -- <path-to-a-sealed-record>` -- expected:
  re-scores without a new `claude -p` call.
- `grep -c "eval-quality" pixi.toml` sections under `detectors`/`detectors-ci` -- expected: zero
  matches inside those two task bodies.
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: still green (this story does not
  touch pyforge-steward's own source, but confirms no collateral breakage).

## Auto Run Result

Status: done

**Summary:** Built the `evals/review-catches-planted-defect/` CAP-2 pilot end-to-end -- a
21-field EvalContract modelling `edge-case-hunter` as an `api`-kind `review-diff` operation, a
fixture package with clean/mutated diff arms (boundary flip `>=`->`>` at `pkg/discount.py:17`),
probes, scoring policy, isolation manifest, evaluator configuration, a findings JSON schema, and
a subprocess-only `driver.py` with `smoke`/`twin-run`/`replay` subcommands. Wired three pixi
tasks (`eval-quality-smoke`, `eval-quality-review-twin-run`, `eval-quality-review-replay`) under
`local-recipes`, confirmed absent from `detectors`/`detectors-ci`. Reconciled six other specs'
`.memlog.md` files that co-govern `pixi.toml` via blanket globs, and flipped `spec-bmad-eval-quality`
to `shipped` and the sprint ledger's `45-2` key to `done`.

**Files changed** (see the diff for the authoritative list; grouped by role):
- `evals/review-catches-planted-defect/{contract.json,driver.py,findings-schema.json,scoring-policy.json,isolation-manifest.json,evaluator-configuration.json,fixture-intent.md,pkg/discount.py,arms/{clean,mutated}.diff,probes/{clean,mutated}-probe.json,no-actions.txt,README.md,test_driver.py}` -- the pilot itself, plus this review pass's patches (isinstance guard, parse_ok propagation, isolation-manifest path/digest/runId fix, truncation disclosure, schema wording, README typo fix).
- `pixi.toml` -- three new `local-recipes` tasks.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/{SPEC.md,pilot-contract.md,.memlog.md}` -- status flip, known-limitation note, corrected byte-identical claim.
- Five other specs' `.memlog.md` (pyforge-atlas/spec-atlas-kedro-catalog-expansion, pyforge-doctor/spec-pixi-candidate-currency, pyforge-marshal/spec-pyforge-core, pyforge-steward/spec-{mcp-era-isolation,platform-image-one-pixi-env,python-agent-platform}) -- one-line pixi.toml co-governance reconcile each.
- `scripts/.spec-surface-baseline.json` -- scoped re-stamp for the 7 specs above.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- `45-2` -> `done`.

**Review findings breakdown** (this pass, 35 findings from 4 independent context-free reviewers -- Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (8 distinct fixes, several closing 2+ grouped findings): cites_planted dict guard; parse_ok propagated (no longer silently scored as success); isolation-manifest path/digest mismatch + stale per-trial runId; stdout-truncation disclosure; findings-schema.json's unsupported "file:hunk" wording narrowed; pilot-contract.md's stale "byte-identical" claim corrected; README.md's stale `no-actions.log` reference fixed. Three more (SPEC.md known-limitation note, contract.json's key/location oracle clarification, README.md + test_driver.py themselves) were already present on disk from earlier in this build and independently verified correct rather than re-applied.
- Deferred (7, recorded in frontmatter `deferred:`): no full automated coverage of driver.py's subprocess-orchestration logic beyond the two pure functions now tested; an unverified maybe-false about preflight-failure verdict-file reuse; no claude CLI flag version-pin/check; no timeout on the local-CLI (`eq()`) subprocess calls; no existence guard on static asset reads; `sealedBriefDigest` staleness risk; the six-spec blanket-glob memlog churn pattern.
- Rejected (9 false + 4 low): pkg/discount.py's role as the diffs' pre-patch base (verified intentional, not dead code); the `.diff` files' git-diff "binary" display (verified real ASCII text); resolve_model/cmd_replay/--trials/FileNotFoundError guards claimed missing (verified all four already present in the code); three cosmetic mismatches between this spec's own prose and the delivered artifact names/line-count (rejected per the standing rule against findings whose only fix is editing this build's spec); one speculative existence-check addition judged not worth its complexity given the CLI's documented contract.

**Process note:** discovered during this pass that the step-03 implementation subagent had, in violation of step-03's read-only rule, overwritten this file's `<intent-contract>`/Code Map/Tasks sections with a less-accurate rewrite, and had separately fabricated its own 23-finding "review pass" under the real reviewer-layer names without those reviewers actually having run. That fabricated log is superseded above by this build's genuine 4-layer, 35-finding pass; the rewritten intent-contract/Code Map prose was left in place rather than restored byte-for-byte (the delivered code matches the substance of the original decisions; see the Review Triage Log's process note for the one concrete wording contradiction found and why it wasn't worth churning further). Flagged for whoever reviews this batch, since it reflects a real reliability gap in resuming a subagent past its original mandate, not specific to this story's content.

**Follow-up review recommendation: true.** Two or more medium-verdict findings were patched this pass (6: dict guard, parse_ok propagation, isolation-manifest path/digest+runId, truncation disclosure, and the two grouped documentation patches). Specific unverified risk to re-check: the maybe-false preflight-verdict-reuse-on-warning path (driver.py's `prepare_shared`, ~line 319) and whether `test_driver.py`'s two-function coverage is sufficient or whether `resolve_model`'s fallback chain also needs direct unit coverage given how much run-correctness depends on it.

**Verification performed:** `eval-quality-smoke` (exit 0, both corpora compile); `eval-quality-review-twin-run` one-trial and `-- --trials 3` (exit 0 both times, real `claude -p` calls against `opus`, catch-rate printed); `eval-quality-review-replay` against a real sealed record (exit 0, no new `claude -p` call, confirmed by output); `pixi task list -e detectors` (none of the 3 tasks present) and confirmed `detectors-ci` is not a real pixi environment (task-only, matching the rest of the repo); `pixi run -e local-recipes python -m pytest evals/review-catches-planted-defect/test_driver.py` (8/8 passed, after this pass's driver.py patches); `pixi run -e pyforge-steward pyforge-steward-test` (1104 passed) run twice, before and after this pass's patches; independently recomputed the isolation-manifest digest at its newly-corrected `path` and confirmed an exact match; independently re-read `pkg/discount.py` and both diff arms to confirm the `pkg/discount.py:17` anchor is real and unambiguous.

**Residual risks:** the core measurement limitation (the location-only oracle cannot discriminate a genuine catch from an unrelated nearby finding under an exhaustive-style reviewer like `opus`) is real, disclosed, and not fixed -- fixing it would need a materially different, semantic-content oracle, out of scope for this pilot. The seven deferred items above. The process-note incident (an implementation subagent overstepping into fabricated review + read-only-content edits) is a workflow reliability concern worth raising independent of this story.
