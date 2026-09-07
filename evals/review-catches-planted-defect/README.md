# review-catches-planted-defect

A `bmad-eval-quality` Behavioral Evaluation Contract (Story 45.2 /
`spec-45-2-the-reviewer-is-measured-against-a-planted-defect`): measures whether the
`edge-case-hunter` review layer catches a planted, one-line boundary-condition defect. A
measurement harness, not a PR gate -- never wired into `detectors`/`detectors-ci`.

## Layout

| File | Role |
|---|---|
| `contract.json` | The `EvalContract` (schema v3). One behavior/oracle; models the review layer as an `api`-kind operation (`review-api`/`review-diff`); its response carries the reviewer's raw `findings` array plus a driver-set `defectPresent` ground-truth field. |
| `pkg/discount.py` | The fixture module under review -- the boundary check lives at line 17. |
| `arms/clean.diff`, `arms/mutated.diff` | The two diffs the twin-run reviews: identical except the mutated arm flips `>=` to `>` at line 17. Standard single-hunk modification diffs (not new-file-addition diffs) so the hunk header's own line math tells the reviewer unambiguously which line changed. |
| `fixture-intent.md` | The tiny "spec this change was built from" the driver hands the reviewer as `claims_file`, so its Step 5 Claims Check has the boundary's documented intent to compare against. |
| `probes/clean-probe.json`, `probes/mutated-probe.json` | AD-9 probes. The clean probe is `probeClass: zero-action` (the only class the `clean-control` qualification route admits) with `expectedClean: true`. The mutated probe is `probeClass: defect` with a `defectSignature` and `manifestationWitness`, both keyed on `defectPresent` rather than the raw findings array -- the AD-40 witness match needs an objective "the defect exists" signal independent of what the reviewer claims. |
| `scoring-policy.json`, `isolation-manifest.json`, `evaluator-configuration.json` | Static templates for the three `eval-quality score` inputs the driver patches per run (model, digests, run id) before writing a per-run copy. |
| `findings-schema.json` | The JSON Schema passed to `claude -p --json-schema`. Wraps `edge-case-hunter.md`'s own bare-array output format in a top-level object (`{"ok": ..., "findings": [...]}`) since the CLI's structured-output validator requires an object at the top level. |
| `no-actions.txt` | Placeholder public-storage referent for the sealed run record's `actionsArtifact` field (this reviewer takes no tool actions). Named `.txt` rather than `.log` -- the repo's blanket `*.log` gitignore rule would otherwise silently drop it. |
| `driver.py` | The subprocess-only driver. Three subcommands: `smoke`, `twin-run`, `replay`. |
| `test_driver.py` | Unit tests for `driver.py`'s pure helpers (`cites_planted`, `parse_review_envelope`) -- no `claude -p` or `eval-quality` calls. |

## How it fits together

1. `driver.py smoke` (pixi: `eval-quality-smoke`) compiles the shipped `bmad-eval-quality` dev
   corpus's own worked example plus this pilot's `contract.json` -- a cheap sanity check that the
   installed CLI and this contract still agree.
2. `driver.py twin-run` (pixi: `eval-quality-review-twin-run`) compiles + seals the contract once,
   preflights both arms, then per trial: invokes `claude -p` headlessly against the
   `edge-case-hunter` layer prompt for each arm's diff, builds a sealed run record from the raw
   findings (adding a `defect`-type finding only when a finding cites the exact planted line --
   see `cites_planted`'s docstring for why an overlapping-but-wider range does not count), and
   scores it with the real `eval-quality score` CLI.
3. `driver.py replay <record>` (pixi: `eval-quality-review-replay`) re-scores a sealed run record
   a prior `twin-run` wrote, using the sibling artifacts in the same `--out-dir`, without invoking
   `claude -p` again.

## Known limitation

The clean arm is a reproducible false-positive source in live testing: `edge-case-hunter`'s
exhaustive-enumeration methodology reliably finds a *different* real boundary concern (float
rounding, NaN handling, etc.) at the same `pkg/discount.py:17`, which the `covers-by-key` oracle's
file:line-only matching cannot distinguish from a true catch. See
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/.memlog.md`
for the full empirical record.
