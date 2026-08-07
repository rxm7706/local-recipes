---
title: 'Ledger-vs-git reconciliation and the versioned status contract'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'd4b746bea868a4b74bf6d0903f3867f2adecdd35'
---

<intent-contract>

## Intent

**Problem:** the tracked `sprint-status-ledger.yaml` twin (the ONE hand-visible, git-tracked feed of "which stories are done") can silently disagree with git reality -- and just did, live, this session: Epic 4's own stories 4.1-4.7 sat at status `review` in the tracked ledger for hours after their PRs had actually merged to `main`, because nothing checked the two against each other. FR-39/FR-40 close this: `marshal status` reports the disagreement as a NAMED discrepancy instead of a downstream consumer (a dashboard, an operator) silently trusting the stale claim.

**Approach:** a NEW pure `core/status.py::reconcile_ledger_vs_git` function (AD-4) compares two independently-gathered sets -- the tracked ledger's own `status: done` story keys (read via `bmad_loop.sprintstatus.load`, the SAME parser `adapters/harness_bmadloop.py` already uses for the Tier-3 feed's identical shape -- reused, never reimplemented, since the ledger IS that feed's promoted twin, written in the same shape) and git's own durably-merged story keys (`core.promotion.merged_story_keys` over `main`'s `commit_subjects`, Story 4.1's own already-shipped machinery) -- and reports BOTH disagreement directions by name: a key marked done in the ledger with no corresponding merge, and the converse, a key durably merged with no corresponding `done` in the ledger. Neither source is ever rewritten (AD-33: git stays the sole repository-fact authority, the ledger read here is diagnostic only). Exposed as a NEW `--reconcile-ledger` flag on the already-shipped `marshal status` command (requires `--project`) -- an opt-in extra read, never folded silently into the default fleet/run-detail views. `schemas/status.json` (NEW, mirroring `schemas/policy.json`'s established shape) publishes the reconciliation payload's own JSON Schema, validated in tests; `data_version` is bumped for this NEW payload shape specifically (the envelope's own `schema_version`/`data_version` split, Story 1.1/AD-39, already exists -- this story is the first `marshal status` output to actually assign a real `data_version` rather than the default).

## Boundaries & Constraints

**Always:**
- **`--reconcile-ledger` requires `--project <slug>`** -- a fleet-wide reconciliation sweep is out of this story's own scope (mirrors Story 5.2's `--run`/`--project` pairing precedent); given without `--project`, refuse before any I/O.
- **The ledger read reuses `bmad_loop.sprintstatus.load`** -- the SAME parser `adapters/harness_bmadloop.py` already imports for the Tier-3 feed's identical shape (`development_status`-keyed, per-story `status` values) -- never a second, hand-rolled YAML parser. Read against `_bmad-output/projects/<slug>/planning-artifacts/sprint-status-ledger.yaml` (the TRACKED twin, not the gitignored Tier-3 feed `marshal status`'s own AD-5 discipline already refuses to read for its live-state views -- this story is explicitly the ONE place in this package that reads it, diagnostically, never as a trust source for live state).
- **Git's own durable-merge evidence reuses `core.promotion.merged_story_keys`** (Story 4.1) over `vcs.commit_subjects(repo_root, "main")` and the project's own composed `merge_subject_template` -- the SAME primitive `marshal deploy promote`/`marshal retire` already trust, never a second detection mechanism.
- **Both disagreement directions are reported, each named explicitly**: `"done-in-ledger-not-merged"` (a key's ledger status is `done`, absent from git's own merged set) and `"merged-not-done-in-ledger"` (a key IS in git's merged set, but the ledger's own status for it is anything other than `done`, including missing entirely) -- this is the live incident's own exact shape (the converse case) and must not be a lesser-supported afterthought.
- **Neither source is ever rewritten** (AD-33) -- this command is read-only, diagnostic; fixing a real discrepancy stays a human/`marshal deploy promote`-driven action outside this story's own scope.
- **`schemas/status.json` publishes the reconciliation payload's own schema** (mirrors `schemas/policy.json`'s established shape/location), validated via `jsonschema.validate` in a new test (mirrors `test_init.py`'s own established `jsonschema.validate(instance=payload, schema=schema)` convention).
- **`data_version` is bumped for this payload** (`build_envelope(..., data_version=2)` or the next real value beyond the default `1`) -- additive fields on an ALREADY-shipped payload shape (Story 5.1/5.2/5.3's fleet/run-detail/escalation fields) never bump either version number (AD-39's own explicit rule); this is a genuinely NEW payload shape, so it earns a real version.

**Never:**
- No rewriting of the tracked ledger, the Tier-3 feed, or any git ref -- purely diagnostic.
- No re-derivation of merge detection or ledger parsing -- both reused verbatim from already-shipped primitives.
- Do not fold `--reconcile-ledger` into the default (no-flag) `marshal status` output -- it is an explicit, opt-in extra read (a YAML parse plus a `git log`-scale operation), never silently added to every invocation's own cost.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--reconcile-ledger` without `--project` | Missing required pairing | Refused before any I/O | Registered finding |
| No discrepancies | Ledger and git agree fully | `data.discrepancies: []`, clean verdict | No finding |
| A story `done` in the ledger, never merged | The "silent stale ledger" case | Named `"done-in-ledger-not-merged"` | No finding (reported, not an error) |
| A story durably merged, ledger status anything but `done` (including absent) | The converse (this session's live incident) | Named `"merged-not-done-in-ledger"` | No finding |
| The tracked ledger file does not exist for a project | Never promoted/synced | Refused with a registered finding naming the missing file | Registered finding |
| A ledger entry with a malformed key | Cannot normalize | Skipped, never a crash (mirrors every other Epic 5 story's established convention) | No finding |
| `--format json` output | Machine-readable consumer | Byte-identical to what a schema-validating consumer (a dashboard generator) can parse without scraping text | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/status.py` -- EDIT. `reconcile_ledger_vs_git(ledger_done_keys, merged_keys) -> tuple[dict, ...]` (pure, AD-4).
- `src/pyforge/marshal/cli/status.py` -- EDIT. `--reconcile-ledger` flag; a new `_reconcile_ledger(...)` orchestration function (reads the tracked ledger via `bmad_loop.sprintstatus.load`, gathers `merged_story_keys`, calls the pure core, emits with `data_version` bumped).
- `src/pyforge/marshal/schemas/status.json` -- NEW. JSON Schema for the reconciliation payload.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register + classify "missing ledger file"/"`--reconcile-ledger` without `--project`" codes.
- `tests/unit/test_status.py` -- EDIT. Reconciliation matrix + `jsonschema.validate` test.

## Design Notes

- **Why this reuses `bmad_loop.sprintstatus.load` rather than a hand-rolled YAML read:** `adapters/harness_bmadloop.py` already imports this exact parser for the Tier-3 feed, and `scripts/promote_sprint_status.py`'s own docstring (quoted in this repo's own `.gitignore`-adjacent tooling) states the tracked ledger is "written in the feed's own shape so `parse_sprint_status` reads both -- no second parser to drift." Reimplementing a second YAML reader here would be exactly the drift that convention was designed to prevent.
- **Why `--reconcile-ledger` is opt-in, not folded into the default view:** the default fleet/run-detail views (Stories 5.1/5.2) are cheap, local-file-only reads bounded by NFR-14's 10-second/7-homes budget; a ledger-vs-git reconciliation adds a YAML parse plus a `git log`-scale walk over `main`'s full history -- a genuinely heavier operation that should be a deliberate ask, not a hidden cost on every `marshal status` call.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Spec Change Log

**1. `HarnessPort` gained a new `ledger_story_statuses(path)` method — a necessary adaptation the spec's own prose ("reuses `bmad_loop.sprintstatus.load`") did not anticipate needing.** AD-3's own import-linter contract (`"only adapters/harness_bmadloop.py may reference bmad_loop"`) forbids `cli/status.py` from importing `bmad_loop.sprintstatus` directly, as the spec's literal wording would require. Fixed by routing the read through a new `HarnessPort` seam (mirroring the existing `story_feed_keys` method's own precedent), keeping the `bmad_loop` import confined to `adapters/harness_bmadloop.py` exactly as the architecture contract requires.

**2. A THIRD finding code, `MRS-STATUS-007` (git history unreadable), beyond the spec's own two named codes — a necessary adaptation.** The spec's own I/O matrix has no row for `vcs.commit_subjects` itself raising (a `main` history read failure); left unhandled, that failure would have silently produced an empty `merged_keys` set, misreporting EVERY ledger `done` key as a false discrepancy. Registered as a hard `UNEVALUABLE` stop, mirroring `cli/deploy.py::MRS-DEPLOY-003`'s identical precedent for the same failure mode.

**3. `confidence` field added to every discrepancy row — a critical, post-implementation-review adaptation to the AC's own literal design.** The AC's "both directions reported as a named discrepancy" reads as symmetric, but the two directions are NOT equally reliable: `merged-not-done-in-ledger` is a POSITIVE git match (proof); `done-in-ledger-not-merged` is an ABSENCE of a match, and `core.promotion.merged_story_keys` has a real, already-documented blind spot for GitHub squash-merge commits (free-form prose subjects, unparseable for a story key) -- this repo's OWN tracked `sprint-status-ledger.yaml` header comment already names this exact failure mode as the reason the ledger exists. Confirmed LIVE: a real run against this repo's own history produced 5 `done-in-ledger-not-merged` rows, zero of them genuine. See Review Triage Log below for the full account.

## Review Triage Log

### 2026-08-07 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 1
- patch: 2 (high 1, low 1)
- defer: 2
- reject: 0
- addressed_findings:
  - `[critical]` `[bad_spec]` **The AC's own symmetric "both directions reported as a named discrepancy" framing does not match the underlying detection mechanism's real reliability -- confirmed LIVE, not hypothetically: a real run against this repo's own tracked ledger and real git history produced 5 `done-in-ledger-not-merged` rows (story keys 1.2, 1.3, 1.6, 1.10, 5.1) for stories that ARE genuinely merged via GitHub squash-merge commits, whose free-form prose subjects `merged_story_keys` cannot parse a story key out of. Zero of the 5 were real discrepancies.** Found by the Blind Hunter, specifically tasked with independently investigating this exact question (per the review prompt's own framing, informed by the implementing engineer's own live smoke-test finding). This repo's OWN `sprint-status-ledger.yaml` header comment already documents this exact failure mode as the reason the tracked ledger exists at all ("the archaeology that failed when squash-merging PR #132 made Epic 10's bmad-loop merge subjects unreachable from main") -- Story 5.4, as literally specified, rebuilds exactly that same archaeology and uses it as an equal-confidence arbiter against the ledger, which would train an operator to distrust the ledger over false alarms on day one. Amended the spec's own design (not merely patched the code): every discrepancy row now carries a `confidence` field (`"confirmed"` for `merged-not-done-in-ledger`, always a positive proof; `"unconfirmed"` for `done-in-ledger-not-merged`, an absence that does not prove non-merger) -- both directions are STILL reported (the AC's own literal requirement, unchanged), but a consumer can now weight them correctly. `schemas/status.json` updated (`confidence` required on every discrepancy entry); text rendering shows it inline; all discrepancy-shaped tests updated.
  - `[high]` `[patch]` **The `--reconcile-ledger`-without-`--project` refusal path (`MRS-STATUS-006`) omitted the REQUIRED `discrepancies` field from its own `data_version: 2` payload, failing the very schema this story ships (`schemas/status.json`'s own `required: ["project", "discrepancies"]`).** Found by the Edge Case Hunter, verified directly against the exact dict the code constructed. Fixed: `data = {"project": None, "discrepancies": []}`. New test assertion + `jsonschema.validate` call added to the existing refusal test.
  - `[low]` `[patch]` **`--run` and `--reconcile-ledger` given together silently let `--reconcile-ledger` win with no signal `--run` was ignored** -- inconsistent with this module's own "reported, never a silent partial" convention. Found by the Edge Case Hunter. Fixed: an explicit mutual-exclusivity refusal (`MRS-STATUS-006`, before any I/O). New test: `test_run_and_reconcile_ledger_together_is_mutually_exclusive`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` D1: `extract_story_key_from_github_merge_subject` (pre-existing, Story 4.1) takes no `project_slug`, a theoretical cross-project false-match risk `--reconcile-ledger` now inherits more directly as a new caller.
  - `[low]` D2: no test exercises a REAL squash-merge-shaped subject (this repo's own dominant landing convention) against the `CONFIDENCE_UNCONFIRMED` tier -- the confidence fix makes the consequence low, but the underlying detection gap itself stays uncovered by a test that would catch a future regression.
- rejected: none this pass.

## Suggested Review Order

**The design-level fix — start here**

- `reconcile_ledger_vs_git`'s new `confidence` tiering and its full rationale comment.
  [`core/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py) — search `CONFIDENCE_CONFIRMED`

- `schemas/status.json`'s updated `discrepancy` shape.

**Correctness fixes**

- The `MRS-STATUS-006` refusal path's `discrepancies: []` fix and the new `--run`/`--reconcile-ledger` mutual-exclusivity check.
  [`cli/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py) — search `mutually exclusive`

**Tests (peripherals)**

- The full reconciliation matrix, `jsonschema.validate` tests, and the two new regression tests from this pass.
</intent-contract>
