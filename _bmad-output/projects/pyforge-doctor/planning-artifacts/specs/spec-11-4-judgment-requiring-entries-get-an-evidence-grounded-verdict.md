---
title: 'Judgment-requiring entries get an evidence-grounded verdict'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '945de2e2c1f3d53ac29a73bc04dbb6505e171032'
final_revision: '46cf7ae664f09d9bdcafd859d91c9dffe46c800a'
---

<intent-contract>

## Intent

**Problem:** Stories 11.1-11.3 select due-for-verification entries, deprioritize churn-free
ones, and mechanically resolve one grep-recomputable claim shape -- but ~306 of the fleet's
308 live due entries carry no mechanical verdict at all (either 11.3 escalated them, or their
claim isn't grep-recomputable in the first place) and genuinely need a human/agent to read the
named code and judge. Nothing today lets that judgment land back on the ledger safely: writing
a `verified:` line by hand is error-prone (wrong vocabulary, a restated claim instead of real
evidence, a stray edit to an unrelated field), and Doctor itself must stay read-only (NFR-1).

**Approach:** A new mutation-only script, `scripts/apply_verification_verdicts.py`, applies a
batch of caller-supplied verdicts (`{project, id, verdict, evidence}`) to tracked
`deferred-work-ledger.md` files -- structurally enforcing CAP-4's evidentiary discipline (a
closed four-verdict vocabulary, non-empty evidence, no restating the entry's own prose) at
write time, and appending a correctly-formatted `verified: <date> — <verdict> — <evidence>`
line per entry. It never judges truth itself -- a human or an agent reading the code still
decides the verdict and writes the evidence text; this script is the safe, disciplined write
path for that decision, mirroring `deferred_work_promote.py`'s established mutation-script shape
(Story 8.3) end to end.

## Boundaries & Constraints

**Always:** Live outside `pyforge.doctor` (Doctor's own `sources/` package stays read-only by
construction, meta-test enforced -- same reasoning `deferred_work_promote.py`'s own docstring
already states). Accept input via `--verdicts-file PATH` (a JSON array of `{"project": str,
"id": str, "verdict": str, "evidence": str}` objects, one or more projects in the same file --
never requires a `--project` flag, since each entry already names its own). Require `--fix`
before writing anything; a bare invocation (no `--fix`) prints usage and exits `2`, writing
nothing -- exact precedent, `deferred_work_promote.py`'s own bare-invocation contract. Validate
a project's WHOLE batch in memory before writing anything for that project; on ANY problem in
that batch, abort with NO write for that project and a clear per-problem message, while a
DIFFERENT project's clean batch in the same run still writes -- exact precedent,
`deferred_work_promote.py`'s `_validate_batch`/`_promote_project` shape. Verdict must be exactly
one of `still-open`, `resolved`, `moot-superseded`, `pending-on-precondition` (lowercase-hyphen,
reusing 11.3's own `mechanical_verdict` token style -- `still-open` is the literal same string in
both layers) -- anything else, including `escalate` (11.3's own internal mechanical-tier signal,
never a terminal CAP-4 verdict), is invalid. Evidence must be non-empty after stripping, and must
NOT normalize (casefold + collapse-internal-whitespace, mirroring `deferred_work_promote.py`'s
own `_normalize_summary`) to the SAME text as the entry's existing `summary:` or `evidence:`
field -- the mechanical half of "never a restatement of the entry's own prose." The entry id must
already exist in the named project's tracked ledger (`_bmad-output/projects/<project>/
planning-artifacts/deferred-work-ledger.md`) -- reject an unknown id, same "no write on an
unresolvable target" discipline as every sibling mutation script. Locate entry spans by
duplicating `chain.py`'s own private `_ENTRY_RE` pattern SHAPE (`r"^#{2,4}\s+(DW-[A-Za-z0-9]
[A-Za-z0-9-]*)"`), never importing the underscore-prefixed symbol -- exact precedent,
`deferred_work_promote.py`'s own stated "reuse the approach, not the private symbol" rule.
Append a NEW `verified:` line (2-space indent, `—` em-dash separators, matching the real ledger
format already in use) after any existing content in the entry's span -- NEVER remove or edit a
prior `verified:` line (re-verification history is additive, mirroring `_verification()`'s own
"take the LAST line" reading convention) and NEVER touch `status:`/`summary:`/`evidence:` or any
other existing field. Write atomically per project (`tempfile.mkstemp` + `os.replace`, matching
`deferred_work_promote.py`'s own precedent), with a re-read-immediately-before-write race check
identical in shape to that script's own. Stamp the CURRENT date (`date.today()`, injectable as a
`today: date | None = None` parameter for tests, matching `chain.py`'s own established pattern)
-- the caller never supplies the date. Never touch `implementation-artifacts/deferred-work.md`
(Tier-3) -- tracked ledgers only.

**Block If:** None -- the verdict vocabulary and the anti-restatement check's exact-normalized-
equality bar (vs. fuzzy matching) are this story's own implementation decisions to make and
record, same as every prior story in this epic.

**Never:** Have this script (or any code) DECIDE a verdict, read named code, or judge whether
evidence is factually true -- that remains a human or agent's job by design (Non-goal, SPEC.md:
"this Spec is agent-driven for judgment-requiring claims by design"); this story ships the safe
write path only. Re-derive Story 11.1/11.2/11.3's due/churn/mechanical selection logic to
restrict which entries are eligible targets -- any existing tracked entry id is a valid target,
selection stays those stories' own concern. Add a `--project` filter flag or any other CLI
surface beyond `--verdicts-file`/`--fix` -- unneeded for this story's own scope. Mutate
`status:`, `summary:`, `evidence:`, or any field other than appending a new `verified:` line.
Attempt fuzzy/semantic restatement detection beyond exact-normalized-equality -- explicit scope
boundary, matching `deferred_work_promote.py`'s own `_validate_batch` precedent for summary
dedup. Retrofit historical free-text verdicts (e.g. "CONFIRMED STILL OPEN") from the 2026-07-30
campaign into the new vocabulary -- pre-existing entries are left as-is (Non-goal: not a full
ledger data-quality audit).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|-----------------|
| Valid verdict applied | real entry id, `verdict: "still-open"`, evidence citing a `file:line`, distinct from the entry's own summary | one new `verified: <today> — still-open — <evidence>` line appended after existing content; exit 0 | No error |
| Invalid verdict token | `verdict: "escalate"` (or any string outside the closed four) | that project's WHOLE batch aborted, no write, message names the bad token and the entry | Non-zero exit |
| Evidence restates the entry's own prose | evidence normalizes identical to the entry's `summary:` (or `evidence:`) field | batch aborted for that project, no write | Non-zero exit |
| Empty evidence | `evidence: ""` or whitespace-only | batch aborted for that project, no write | Non-zero exit |
| Unknown entry id | id not present in the named project's tracked ledger | batch aborted for that project only; a different clean project in the same run still writes | Non-zero exit overall |
| Duplicate (project, id) in one input file | the same pair appears twice, possibly with different verdicts | batch aborted for that project, message names both occurrences | Non-zero exit |
| Re-verification | entry already carries one or more prior `verified:` lines | new line appended after the last one; every prior line byte-identical, untouched | No error |
| Concurrent ledger change mid-run | tracked ledger file changes between the initial read and the write | write aborted for that project, no overwrite of the concurrent change | Non-zero exit |
| No `--fix` | any invocation lacking `--fix` | nothing written anywhere; usage text printed | Exit code 2 |

</intent-contract>

## Code Map

- `scripts/apply_verification_verdicts.py` (NEW) -- the mutation-only writer/validator: CLI
  (`--verdicts-file PATH --fix`), per-project batch validation, atomic write. Mirrors
  `scripts/deferred_work_promote.py`'s module shape end to end (docstring rationale for living
  outside `pyforge.doctor`, `_is_file`/`_probe` duplicated-shape helpers, `_Outcome` dataclass,
  per-project try/except isolation in `main()`).
- `tests/scripts/test_apply_verification_verdicts.py` (NEW) -- coverage, one test per I/O matrix
  row plus system-level ACs. Mirrors `tests/scripts/test_deferred_work_promote.py`'s
  `_patched_*`-copies-the-script-into-tmp_path + `subprocess.run([sys.executable, ...])` fixture
  pattern exactly (no `pyforge.doctor` import needed here, since this script duplicates rather
  than imports its one regex dependency -- simpler fixture setup than the promoter's own test).

## Tasks & Acceptance

**Execution:**
- [x] `scripts/apply_verification_verdicts.py` -- create module docstring + `REPO_ROOT`,
  `_VERDICTS` frozenset, duplicated `_ENTRY_RE`, `_is_file`/`_probe` (duplicated shape from
  `deferred_work_promote.py`, not `chain.py`, since this script has no other dependency on
  Doctor's package).
- [x] `scripts/apply_verification_verdicts.py` -- `_normalize(text)` (casefold + collapse
  whitespace, mirrors `_normalize_summary`) and `_entry_spans(text)` (id -> (start, end, fields)
  boundary walk over `_ENTRY_RE` marks, extracting each entry's `summary:`/`evidence:` field
  values for the anti-restatement check).
- [x] `scripts/apply_verification_verdicts.py` -- `_load_verdicts(path)` parses and structurally
  validates the JSON input shape (list of objects with the four required string keys); a
  malformed file is a top-level usage error (exit 2), not a per-project batch failure.
- [x] `scripts/apply_verification_verdicts.py` -- `_validate_project_batch(entries_by_id, items)`
  -- pure, in-memory: verdict-vocabulary check, non-empty-evidence check, anti-restatement check,
  unknown-id check, duplicate-(project,id)-within-batch check. Returns a list of problem strings
  (empty = clean).
- [x] `scripts/apply_verification_verdicts.py` -- `_apply_project(project, items, today)` --
  snapshot-then-validate-then-race-recheck-then-atomic-write, mirroring `_promote_project`'s
  shape; formats and inserts each new `verified:` line at the correct entry span end.
- [x] `scripts/apply_verification_verdicts.py` -- `main()` -- argparse (`--verdicts-file`,
  `--fix`), groups input items by project, calls `_apply_project` per project inside its own
  try/except (one project's crash isolated from a sibling's clean run), prints one outcome line
  per project, non-zero exit on any failure.
- [x] `tests/scripts/test_apply_verification_verdicts.py` -- one test per I/O matrix row (9)
  plus the three system-level ACs below; synthetic tracked-ledger fixtures (matching
  `test_deferred_work_promote.py`'s own `_MASON_EXISTING_TRACKED`-style precedent).

**Acceptance Criteria:**
- Given a verdicts-file naming a real entry with a valid verdict token and evidence that does not
  restate the entry's own prose, when run with `--fix`, then the tracked ledger's entry gains
  exactly one new `verified: <today> — <verdict> — <evidence>` line appended after existing
  content, and no other field of that entry changes.
- Given no `--fix` flag, when the script is invoked, then nothing is written anywhere and the
  script exits non-zero (`2`) with usage/purpose text.
- Given a verdicts-file spanning two projects where one project's batch is invalid and the
  other's is clean, when run with `--fix`, then the clean project's ledger is written, the
  invalid project's ledger is left byte-identical to its pre-run state, and the overall exit
  code is non-zero.

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 3, medium 0, low 5)
- defer: 2: (medium 0, low 2)
- reject: 5: (medium 1, low 4)
- addressed_findings:
  - `[high]` `[patch]` `project` was joined directly into `tracked_path` with no validation against the real discovered project set (`REPO_ROOT / "_bmad-output" / "projects" / project / TRACKED_REL`) -- `Path.__truediv__` silently discards everything to its left when the right operand is absolute, so an absolute or `..`-laden `project` string could resolve entirely outside `_bmad-output/projects/`; verified empirically (Blind Hunter + Edge Case Hunter, same finding). Fixed by adding `_known_projects()` (mirrors `deferred_work_promote.py`'s own `_project_slug_map`/`unknown project(s):` precedent, which this script's Design Notes claimed to mirror "end to end" but had dropped) and rejecting any `project` not a real discovered directory, before any path is built. Three new regression tests (unknown slug, absolute-value escape attempt with a planted target ledger, empty-string value).
  - `[high]` `[patch]` The anti-restatement check (`_validate_project_batch`) was structurally inert for the flat `review-budget-followup` entry shape (`_ENTRY_FLAT` in the test fixture): that shape carries `reason:`, not `summary:`/`evidence:`, so `_FIELD_RE` never captured it, `fields` came back empty, and the "evidence restates the entry's own prose" guard could never fire for an entire documented, tested-as-valid shape (Blind Hunter + Edge Case Hunter, same finding). Fixed by extending `_FIELD_RE` and the restatement-check loop to also recognize `reason:`. New regression test proves restatement is now caught for the flat shape.
  - `[high]` `[patch]` `_format_verified_line` only `.strip()`s (trims edges) and never rejects an embedded newline in `evidence`, so a multi-line evidence string would write a stray, unindented physical line into the ledger matching no `_FIELD_RE`/`_ENTRY_RE` pattern -- breaking the single-physical-line-per-field invariant this script's own `_entry_spans` docstring assumes (Blind Hunter + Edge Case Hunter, same finding). Fixed by rejecting evidence containing `\n`/`\r` in `_validate_project_batch`. New regression test.
  - `[low]` `[patch]` The 4th and last closed-vocabulary member, `pending-on-precondition`, had zero test coverage (Edge Case Hunter). Added a dedicated regression test.
  - `[low]` `[patch]` `test_valid_verdict_appends_one_new_verified_line_and_exits_zero`'s `for line in before.splitlines(): assert line in after` is near-a-no-op for blank lines, since `"" in after` is trivially true for any non-empty string -- it did not actually verify blank-line spacing/structure around the target entry is preserved (Blind Hunter). Added a new test asserting the exact line-by-line sequence (one blank line before/after the new `verified:` line) instead.
  - `[low]` `[patch]` The module docstring's "Never mutates... any field other than appending a brand-new `verified:` line" overstated what happens on disk: `_apply_verdicts_to_text` `.rstrip()`s the entry's span and reinserts a fixed `"\n\n"` before the new line, normalizing trailing blank-line COUNT within the span even though no field's TEXT changes (Blind Hunter). Docstring corrected to name this precisely.
  - `[low]` `[patch]` `test_bare_invocation_explains_purpose_and_does_not_write` asserted `"verified:" in r.stderr or "verdict" in r.stderr` -- the `or` let either substring alone satisfy the test, so a near-empty stderr containing just one word would pass (Blind Hunter). Tightened to require both plus the literal vocabulary token `"still-open"`.
  - `[low]` `[patch]` The test fixture's `_patched_script` wrote the copied script to `scripts/verdicts_applier.py`, not `apply_verification_verdicts.py` -- harmless but confusing for a future maintainer grepping test output for the real filename (Blind Hunter). Renamed to match.
  - `[low]` `[defer]` A tracked ledger with two entries sharing the identical `DW-` id (a pre-existing, malformed/invariant-violating ledger) makes `_entry_spans`'s dict-building loop silently overwrite the first occurrence's span with the second's, so a verdict lands on only one of them with no error surfaced (Edge Case Hunter). Bounded (requires a pre-existing malformed ledger, none observed live) and matches this epic's own already-adjudicated precedent (Story 11.1/11.2/11.3's read-only `_check_project_due_for_verification` accepts the identical risk class for the identical reason) -- Non-goal: "not a full ledger data-quality audit of pre-existing issues." Minted `DW-FU-11-4`.
  - `[low]` `[defer]` Nothing prevents the same verdicts-file from being applied twice across two separate runs, silently appending a byte-identical duplicate `verified:` line with no diagnostic distinguishing an accidental re-run from a genuine repeated re-verification (Blind Hunter). Genuinely ambiguous scope (what counts as "the same verdict"?), and the story's own Boundaries caution against expanding the CLI surface without a stated requirement. Minted `DW-FU-11-4-2`.
  - `[medium]` `[reject]` The atomic-write race check narrows but does not fully close the TOCTOU window between the re-check read and `os.replace` (no file locking) (Blind Hunter + Edge Case Hunter, same finding) -- already-adjudicated, identical precedent in `deferred_work_promote.py`'s own docstring ("True cross-process locking is out of scope; this narrows the race window to the write call itself"), which this story explicitly mirrors; not a new gap.
  - `[low]` `[reject]` A markdown heading nested inside an entry's own summary/evidence prose could misplace the heading-bounded span (Edge Case Hunter) -- bounded to a pre-existing multi-line field value, which the newline-rejection patch above makes structurally impossible for any NEWLY-applied content; for pre-existing ledger text, correctly stopping at that heading is `_HEADING_RE`'s own designed purpose, not a bug.
  - `[low]` `[reject]` No `--json`/structured output mode for automation callers (Blind Hunter) -- the spec's own Boundaries explicitly state "Never: Add flags beyond what's needed"; not a gap, a documented scope decision.
  - `[low]` `[reject]` The scoped baseline-stamp hunk also updates `pyforge-steward/spec-python-agent-platform`'s hashes, read as scope creep (Blind Hunter) -- both specs jointly govern the shared root `pixi.toml` (an established, already-documented cross-package reconciliation convention in this repo, confirmed in `spec-python-agent-platform`'s own memlog), not an unrelated bundle.
  - `[low]` `[reject]` The baseline-stamp hunk updates `chain.py`'s hash with no corresponding content diff visible in the reviewed diff, read as unexplained (Blind Hunter) -- confirmed empirically (`git diff baseline_revision -- chain.py` is empty): `chain.py`'s content is genuinely unchanged since `baseline_revision`; the stored hash at `baseline_revision` was itself stale from an earlier cherry-pick conflict resolution in this same session (accepted an intermediate commit's hash instead of the final one), corrected by this pass's own scoped `--write-baseline` re-stamp. No new drift.

## Design Notes

- Mirrors `deferred_work_promote.py`'s established shape end to end (Boundaries) rather than
  inventing a new mutation-script pattern: mutation-only, lives in `scripts/` not
  `pyforge.doctor`, duplicated-not-imported private parsing shapes, in-memory whole-batch
  validation before any write, atomic tempfile+`os.replace`, one write per project, `--fix`-gated,
  no pixi task (that precedent's own docstring: "plain `python`, no pixi task").
- The four-verdict vocabulary intentionally reuses Story 11.3's own lowercase-hyphen
  `mechanical_verdict` token style (`still-open` is the literal same string in both layers)
  rather than the free-form ALL-CAPS prose the 2026-07-30 campaign used by hand
  (`precedent-2026-07-30-campaign.md`) -- a fixed, parseable vocabulary is what Story 11.7's
  future fleet-picture staleness percentage will need to compute reliably from raw ledger text.
  Historical entries keep their free-form verdicts unchanged; only newly-applied verdicts use the
  new vocabulary.
- The anti-restatement check is intentionally a narrow, mechanical proxy for CAP-4's real
  requirement ("never a restatement of the entry's own prose") -- exact-normalized-equality
  catches the sharpest failure mode (an agent literally echoing the claim back) without
  attempting fuzzy/semantic similarity, which would risk false-positiving on legitimate short
  evidence that happens to share a few words with the summary.
- This script does not re-derive who is "due" (Story 11.1), churn-skipped (11.2), or
  mechanically-resolved (11.3) -- any existing tracked entry id is a valid target. Restricting
  targets here would duplicate three stories' own selection logic for no stated benefit; a
  human or agent calling this script already knows which entry it just investigated.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Shipped `scripts/apply_verification_verdicts.py`, the mutation-only "safe write path"
CAP-4 needs: given a `--verdicts-file` (JSON array of `{project, id, verdict, evidence}`), it
validates each named project's WHOLE batch in memory -- closed four-verdict vocabulary
(`still-open`/`resolved`/`moot-superseded`/`pending-on-precondition`), non-empty single-line
evidence that does not restate the entry's own prose, the id exists, the project is real -- and,
only on a clean batch, appends one new `verified: <date> — <verdict> — <evidence>` line to each
named entry's span in its project's tracked `deferred-work-ledger.md`. It never judges truth
itself; a human or agent investigating a due entry still decides the verdict and evidence text.
Mirrors `deferred_work_promote.py`'s established mutation-script shape end to end (Story 8.3).

Before this story's own implementation could begin, this worktree's baseline predated Story
11.3's actual landing (a stuck-orchestrator-baseline situation: 11.3's two commits existed only
on its own sibling bmad-loop worktree branch, never merged into the shared `loop/pyforge-doctor`
branch this worktree forked from, even though the tracked sprint-status ledger already read
`11-3: done`). Cherry-picked both of 11.3's real commits onto this branch before drafting the
Story 11.4 spec, resolving three bookkeeping-file conflicts (two append-only memlogs, one
project-scoped spec-surface baseline stamp) by hand; verified the merged state matches 11.3's own
claimed final state exactly (983 passed, 2 skipped, live `due-for-verification-check` showing the
same `mechanical_verdict: escalate` entry). A stray unscoped `--write-baseline` run during that
recovery (which would have accepted ALL 80 specs' pending drift repo-wide) was caught and
corrected to a properly scoped `--spec pyforge-doctor/spec-pyforge-doctor --spec
pyforge-steward/spec-python-agent-platform` re-stamp before any of it landed.

**Files changed:**
- `scripts/apply_verification_verdicts.py` (NEW) -- the writer/validator: `REPO_ROOT`,
  `_VERDICTS` frozenset, duplicated `_ENTRY_RE`/`_HEADING_RE`/`_FIELD_RE`, `_is_file`/`_probe`,
  `_normalize`, `_entry_spans` (heading-bounded span, a deliberate divergence from `chain.py`'s
  own next-DW-mark-bounded `_verification()` -- real tracked ledgers interleave `DW-` entries
  with unrelated `## Deferred from: ...` section headings, confirmed live in
  `pyforge-warden`'s own ledger, and a WRITE path needs the tighter boundary a READ-only
  staleness check does not), `_known_projects`, `_load_verdicts`, `_validate_project_batch`,
  `_format_verified_line`, `_apply_verdicts_to_text`, `_apply_project`, `_Outcome`, `main()`.
- `tests/scripts/test_apply_verification_verdicts.py` (NEW) -- 30 tests: one per I/O matrix row,
  the three system ACs, plus 7 review-driven regression tests (below).
- `scripts/.spec-surface-baseline.json` -- scoped re-stamp for the two specs Story 11.3's real
  commits touch (`pyforge-doctor/spec-pyforge-doctor`, `pyforge-steward/spec-python-agent-
  platform`); corrects a stale `chain.py` hash left over from this session's own 11.3
  cherry-pick conflict resolution (an intermediate commit's hash was accepted instead of the
  final one) -- confirmed empirically that `chain.py`'s content itself is byte-identical to
  `baseline_revision`, zero new drift.

**Review findings breakdown (Blind Hunter + Edge Case Hunter, independent, no shared context):**
8 patched (3 high, 5 low), 2 deferred (both low, tracked ledger entries `DW-FU-11-4`/
`DW-FU-11-4-2`), 5 rejected (1 medium, 4 low -- matched established precedent, explicit Boundaries
scope decisions, or review-context confusion resolved by direct verification). Full detail in the
Review Triage Log above. All 3 high-severity patches were genuine correctness gaps in the
script's own core safety purpose: no validation that `project` resolves inside
`_bmad-output/projects/` (path-traversal risk, `Path.__truediv__` silently drops everything left
of an absolute right operand -- verified empirically), the anti-restatement check structurally
inert for the flat `DW-FU-*`/`reason:` entry shape (one of two documented live shapes), and no
rejection of an embedded newline in evidence (would corrupt the ledger's one-physical-line-per-
field format). Zero `intent_gap`, zero `bad_spec` -- the spec's own Boundaries and vocabulary
design held; only the mechanical validation LOGIC needed the fixes above.

**Verification performed (all green, after the patch pass):**
- `pixi run -e local-recipes python -m pytest tests/scripts/test_apply_verification_verdicts.py -v`:
  30 passed (23 original + 7 review-driven regression tests).
- `pixi run -e local-recipes python -m pytest tests/scripts -q`: 123 passed, 8 skipped (no
  regression to any sibling test file).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 983 passed, 2 skipped (unchanged --
  this story touches nothing under `pyforge.doctor`).
- `ruff check scripts/apply_verification_verdicts.py tests/scripts/test_apply_verification_verdicts.py`:
  All checks passed.
- `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface`: zero findings for
  `pyforge-doctor`/`pyforge-steward` after the scoped baseline re-stamp (pre-existing drift in
  three unrelated projects -- scribe, warden, marshal -- confirmed untouched by this story).

**Residual risk.** Low. The two deferred findings are both bounded (require a pre-existing
malformed ledger, or an operator re-running the exact same verdicts-file twice) and match this
epic's own already-established precedent for how to treat this failure class. This script is
never invoked automatically -- no pixi task, `--fix`-gated, whole-batch-validated-before-any-write
-- so its blast radius on any single bad invocation is at most one project's tracked ledger,
recoverable from git history. The stuck-orchestrator-baseline recovery performed before this
story's own work began is itself a known, documented fleet pattern (see auto-memory
`project_the-stuck-orchestrator-baseline-bug...`); the recovery here was verified against 11.3's
own claimed final state byte-for-byte (983/2 skipped, identical live fleet output) before any
Story 11.4 code was written on top of it.

