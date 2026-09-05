# Pilot contract — CAP-2 shape (HOW)

**Layout** `evals/review-catches-planted-defect/`: a tiny fixture package; `arms/clean.diff` and
`arms/mutated.diff` (one boundary flip, `>=` → `>` at `pkg/discount.py:17`); the contract —
interface `review-api`, operation `review-diff`, `permittedInterfaces.kind = api` (the only kind
schema v0 compiles), 21 required top-level fields modelled on
`corpus/dev/contracts/satisfied-declarations.json`; probes; scoring policy; isolation manifest;
evaluator configuration; a findings JSON schema.

**Driver** (~150 lines, `subprocess` only): runs the `edge-case-hunter` layer headlessly —
`claude -p --output-format json --json-schema <findings-schema> --max-budget-usd 2
--no-session-persistence`, model pinned to the station's `[adapter.review].model` — maps exit code
+ parsed findings (`location` = `file:line`) to an observation, emits the sealed run record. The
layer prompt is `.claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md` (byte-identical
to the `bmad-code-review` copy); "Return ONLY a valid JSON array" is why this layer is measurable
and the prose review is not.

**Oracle** one strong oracle: `covers-by-key` over `referenceSets.planted-defects`
(`["file","line"]`) against the review's cited locations. "The review ran" never passes on its own.

**Tasks** `eval-quality-smoke` (corpus compile), `eval-quality-review-twin-run -- --trials N`,
`eval-quality-review-replay`. Never in `detectors` — this measures the reviewer, not the PR.

**Upstream facts that bind** (re-verified 2026-09-05): `score` / `runScore` / `ingest` exist only on
main (package.json 0.2.0, HEAD 3172162f); no runtime schema-version check → exact pin; the shipped
`examples/bmad-tea-contract.json` (kind cli, 7 of 21 fields) is illustrative and will not compile.
