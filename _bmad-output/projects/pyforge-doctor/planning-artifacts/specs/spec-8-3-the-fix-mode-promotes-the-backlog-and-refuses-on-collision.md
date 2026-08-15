---
title: 'Story 8.3: The fix mode promotes the backlog and refuses on collision'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: '95b09e1b2fb0e10058478e966638f3b3a1dd6f39'
final_revision: 'd2617c4036'
---

<intent-contract>

## Intent

**Problem:** Story 8.1 classifies every legacy Tier-3 shape; Story 8.2 mints
a collision-free id for any orphan. Neither writes anything (Doctor's
`sources/` package is read-only by construction, meta-test enforced). The
72-entry live legacy backlog (marshal 30, steward 38, mason 2, herald 2)
still has no way to actually reach the tracked ledger except the by-hand
process that already shipped two real bugs (a false-orphan content
duplication, a 10x overcount) during the 2026-08-15 audit.

**Approach:** A new standalone script, `scripts/deferred_work_promote.py`
`--fix [--project SLUG ...]`, mirroring `scripts/spec_surface_check.py`
`--write-baseline`'s established pattern: duplicates nothing from
`pyforge.doctor` internals it doesn't need to, but safely IMPORTS Story
8.1/8.2's pure, read-only `classify_tier3_entries`/`mint_id_for_entry`
(importing a pure function is not a write site — only the script's own
`write_text` call is). Computes every promotion for a project fully in
memory, validates zero id/summary collisions, then writes the tracked
ledger once — never Tier-3 (append-only, untouched) and never the
grandfather baseline (Story 8.4's job).

## Boundaries & Constraints

**Always:** For each target project, source orphans from
`classify_tier3_entries(tier3_path)` filtered to `entry.id is None`
(`LEGACY_FLAT`/`LEGACY_HEADER` — `IDENTIFIED_*` entries are already
excluded by construction, which is what makes false-orphan re-promotion of
already-headed content structurally impossible here, unlike the by-hand
process). Mint each orphan's id via `mint_id_for_entry`, threading one
running `already_minted` set per project across the whole batch (Story
8.2's own proven discipline — skipping this reproduces the exact 24x
duplicate-mint bug that story's own review caught). Before writing, verify
in memory: no two to-be-appended entries share an id or byte-identical
`summary` text, and no to-be-appended id or summary already exists in the
tracked ledger — if any collision is found, abort with **no write at all**
for that project (existing tracked file, if any, is byte-identical to its
pre-run state). Promoted entry format (verified against real promoted
entries already in 3+ tracked ledgers): `### {id}: {summary}` header,
followed by a `- source_spec:` block whose 2-space-indented continuation
lines are `summary:`, `evidence:`, `promoted: {date} — promoted from
Tier-3 {relative tier3_path} (legacy {shape} entry, no prior id)`, and
`status: open` — same shape every real promoted entry already uses, no new
syntax. Scope per `--project` the same way `sprint-ledger-sync` does
(default: every project with a Tier-3 file; narrow with repeatable
`--project`) — a collision in one project's batch must not block another
project's clean batch.

**Block If:** a project's Tier-3 file has zero orphans (nothing to
promote) -- not an error, just a no-op for that project, reported as such.

**Never:** modify the Tier-3 file itself (append-only by this repo's
established convention — `do not modify existing entries`) or the
grandfather baseline (`scripts/.deferred-work-baseline.json`) — re-stamping
that is explicitly Story 8.4's job, deliberately sequenced after this one.
Write via multiple incremental appends — compute the full new file content
in memory and call `write_text` exactly once per project on success.
Import anything from `pyforge.marshal` or any other station package (same
fleet-wide rule Story 8.1/8.2 already honor).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean batch | N real orphans, no collisions | N entries appended, one write, ids reported | exit 0 |
| No orphans | project's Tier-3 has only IDENTIFIED_* entries | no-op for that project, reported | exit 0 |
| Manufactured duplicate id | a fixture with two orphans that would mint/already-carry the same id | abort for that project, tracked ledger unchanged | non-zero exit |
| Manufactured duplicate summary | a fixture with two orphans sharing byte-identical `summary` text | abort for that project, tracked ledger unchanged | non-zero exit |
| Multi-project run | `--fix` with no `--project` (all 8) | each project's outcome independent -- one project's collision does not block another's clean promotion | mixed exit acceptable, reported per-project |
| Missing Tier-3 file | project has no `implementation-artifacts/deferred-work.md` | no-op, not an error | exit 0 |

</intent-contract>

## Code Map

- `scripts/deferred_work_promote.py` -- new. `--fix [--project SLUG ...]`. Imports `classify_tier3_entries`/`mint_id_for_entry`/`Tier3Shape` from `pyforge.doctor.sources.chain` (read-only imports; this script owns the only write site).
- `tests/scripts/test_deferred_work_promote.py` -- new. Subprocess-based, mirroring `tests/scripts/test_deferred_work_baseline.py`'s `_patched_*`/`REPO_ROOT`-substitution/tmp-fixture-repo pattern.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/deferred_work_promote.py` -- CLI (`argparse`, `--fix`, repeatable `--project`), per-project promotion pipeline (classify -> filter orphans -> mint with a running `already_minted` set -> in-memory collision validation -> single `write_text` on success), promoted-entry formatter matching the verified real shape exactly.
- [x] `scripts/deferred_work_promote.py` -- collision validation: byte-identical `summary` text and exact id equality, checked both within the current batch and against the tracked ledger's existing content (reuse `_ids`-style token harvesting for the id half; a straightforward set-membership check on extracted `summary:` values for the text half).
- [x] `tests/scripts/test_deferred_work_promote.py` -- clean-batch test against a real excerpt (a small slice of one project's real orphan backlog); manufactured duplicate-id and duplicate-summary fixtures, each asserting non-zero exit and the tracked ledger file byte-identical to its pre-run snapshot (or absent, if it didn't exist before); multi-project independence test (one project collides, a sibling project's clean batch still writes); Tier-3 file provably untouched (byte-identical) after every run, success or failure.

**Acceptance Criteria:**
- Given the real 72-entry legacy backlog (marshal/steward/mason/herald), when `--fix` runs, then every genuine orphan is promoted with zero content duplication (no already-`IDENTIFIED_*` entry is ever re-promoted, structurally guaranteed by sourcing only `entry.id is None` results from Story 8.1's classifier) and `tier3-only-deferral` clears for every newly-promoted id (each now has a tracked twin). `tier3-entry-unidentified` does NOT fully clear from this story alone -- see Design Notes; that finding is baseline-count-driven and needs Story 8.4's re-stamp too, correcting the epics.md AC's own imprecise wording on this point.
- Given a manufactured fixture with two orphans sharing byte-identical `summary` text, when `--fix` runs, then the write aborts for that project and the tracked ledger is byte-identical to its state before the run.
- Given a multi-project `--fix` run where one project's batch collides, when it runs, then every OTHER project's clean batch still writes successfully.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10 (high 4, medium 4, low 2)
- defer: 0
- reject: 1 (low 1)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter reproduced a real, confirmed data-loss race: `_promote_project` reads the tracked ledger once, does all validation, then writes once with no re-check -- a concurrent writer's change landed in that window is silently destroyed and the run still reports success. Fixed: immediately before the terminal write, re-read the tracked file and abort (reporting the race, no write) if it no longer matches the snapshot used for validation -- converts silent data loss into a loud, safe abort. True cross-process locking is out of scope (no precedent anywhere else in this repo); this narrows the window from "the whole batch's mint+validate phase" to the write call itself, which is the load-bearing property the story's own "no partial output" ethos wants.
  - `[high]` `[patch]` Blind Hunter found `write_text` truncates the destination before writing -- a crash mid-write (OOM/SIGKILL/disk-full) can leave the tracked ledger truncated or corrupted, and unlike the cited `spec_surface_check.py`/`deferred_work_baseline.py` precedent (fully-regenerable derived JSON, safe to lose), a promoted tracked ledger is durable, non-regenerable content. Blind Hunter found a BETTER in-repo precedent not used: `scripts/seed_claude_consent.py`'s `tempfile.mkstemp` + `os.replace`. Fixed: switched to that pattern.
  - `[high]` `[patch]` Blind Hunter found, live-confirmed against real data (13 of 76 real orphans today), that promotion silently drops any orphan field outside `{source_spec, summary, evidence}` (e.g. a `resolution:` field signaling the matter was already addressed) and unconditionally force-overwrites any existing `status:` an orphan bullet carries with `status: open` -- risking an already-resolved item resurfacing as freshly open with no trace of why it was previously handled. Traces to this story's own intent-contract (the Boundaries section's literal field list), but resolves via exactly one natural reading matching this story's own "promotion is verbatim, never curative" principle: preserve any additional fields verbatim, and only default `status:` to `open` when the orphan doesn't already specify one. Resolved as a direct patch, not an intent_gap loopback.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found an I/O error (`OSError` from `mint_id_for_entry`'s `_collect_dw_tokens`, `IsADirectoryError` from a tracked path that's a directory, or any other unexpected exception) is not caught anywhere in `_promote_project`/`main()` and crashes the ENTIRE multi-project run, leaving every alphabetically-later project unprocessed -- directly undermining the spec's own "one project's collision must not block a sibling's clean promotion" AC, which the test suite only verified for the validation-abort path, not the I/O-error path. Fixed: wrap each project's processing in `main()`'s loop with a per-project exception boundary (mirrors `chain.py`'s own `degrade_on_exception` philosophy, which this new script hadn't carried forward) -- a crash in one project reports as that project's own failure and every other project still runs.
  - `[medium]` `[patch]` Edge Case Hunter found a permission-denied `tier3_path` (or an unreadable ancestor directory) makes bare `Path.is_file()` silently return `False`, so a real, unpromoted backlog reports as "nothing to promote" -- a dangerous false negative. Fixed: reuse `chain.py`'s own raising `_probe`-style check instead of bare `.is_file()` (the exact anti-pattern that helper already exists to prevent, per its own docstring citing prior real incidents).
  - `[medium]` `[patch]` Blind Hunter found the mint-time `ValueError` abort path (an orphan later in a batch fails to mint after earlier orphans already succeeded) has no test proving the batch is fully aborted with no partial write -- the one declared failure mode in the I/O matrix without dedicated coverage, sitting squarely in the "no partial output" property the story cares most about. Fixed: added.
  - `[medium]` `[patch]` Edge Case Hunter found a blank or whitespace-only `summary` field defeats the collision guard (two blank-summary orphans are not recognized as duplicates, silently promoted as distinct). Fixed: a blank/whitespace-only summary is now always treated as a validation failure (blocks that entry's promotion) rather than silently exempted from dedup.
  - `[medium]` `[patch]` Blind Hunter found the exact-byte-match collision guard misses the real-world failure mode its own docstring names (a summary lightly reworded/whitespace-normalized during a by-hand promotion pass). Full fuzzy/near-duplicate matching is out of scope (real complexity increase, false-positive risk, not requested by this story's AC). Fixed the cheap, well-scoped sub-case: normalize (casefold + collapse whitespace) before comparing, catching the "differs only in whitespace/casing" variant Blind Hunter specifically named. Full fuzzy dedup logged as a residual risk, not implemented here.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found `_project_slug_map`'s short-name derivation (`removeprefix("pyforge-")`) has no uniqueness check -- two directories colliding on the same short slug would silently clobber one dict entry, making a project unreachable via `--project` with no error. Fixed: raises on a detected collision instead of silently overwriting.
  - `[low]` `[patch]` Edge Case Hunter found a `tracked_path` that resolves to a directory produces a generic crashed-with-traceback message once the broad exception boundary (above) catches it. Fixed: added an explicit, friendlier upfront check naming the specific problem for this plausible operator mistake.
  - `[low]` `[reject]` Blind Hunter found a typo'd `--project` value that happens to collide with an unrelated real directory name silently succeeds as a no-op rather than erroring as "unknown project." Rejected: Blind Hunter's own review frames this as intentional per the module's documented discovery-vs-validation scope split, already covered by a passing test for the current behavior, and low real-world risk given the fleet's small, `pyforge-*`-prefixed project set.

## Design Notes

**Correcting the epics.md AC and SPEC.md CAP-6's "tier3-entry-unidentified
clears" claim.** `tier3-entry-unidentified` findings come from
`_anonymous(t3_path)[count:]` -- a POSITIONAL slice past the grandfather
baseline's stamped count, entirely a function of Tier-3 file content and
the baseline count. This story deliberately never touches either (Tier-3
is append-only; the baseline is Story 8.4's). Promoting an entry into the
tracked ledger clears `tier3-only-deferral` (an id-set-difference check
between Tier-3 and tracked) but cannot mathematically move
`tier3-entry-unidentified`'s baseline-relative count. The epics.md/CAP-6
text describes the EPIC-level outcome (8.3 + 8.4 together, both required
to fully clear the fleet's finding set) using Story-8.3-only language --
matches the same class of imprecision Story 8.1 already found and
corrected in this same epic (the shape-4 paraphrase). Ground this story's
own AC in what `--fix` alone can mathematically achieve.

Duplicate-content protection is structurally different from what the
by-hand process got wrong. That process re-promoted content that ALREADY
had an id elsewhere (false-orphan duplication) -- impossible here by
construction, since this story only ever sources `entry.id is None`
results from Story 8.1's classifier, which already correctly excludes
`IDENTIFIED_*` shapes. "Zero content duplication" here instead means: no
two DIFFERENT orphan entries (a genuine copy-paste duplicate in Tier-3, or
an adversarial test fixture) get promoted as if they were distinct
findings.

**Implementation note: the live backlog counts in this story's own Intent
("marshal 30, steward 38, mason 2, herald 2") are stale relative to
`classify_tier3_entries` run live at implementation time (2026-08-15) --
actual live orphan counts were far higher (marshal 231, steward 91, mason
25, herald 39). This does not change the story's design; it changed which
data the smoke test exercised.** Confirmed live during implementation: 4 of
mason's 25 real orphans already collide, by byte-identical `summary` text,
with entries already promoted into the tracked ledger by the historical
by-hand process (their Tier-3 bullets were never retroactively given a
header, since Tier-3 is append-only) -- running `--fix --project mason`
against a full copy of the real backlog correctly ABORTS with 4 named
collisions and zero write, exactly the hazard this story's `summary`-text
guard exists to catch. A curated subset (the same backlog minus those 4
already-tracked entries) promotes cleanly: 21 orphans, ids `DW-1-8-1`
through `DW-2-3-4`, format verified byte-for-byte against the real
`DW-FU-6-4` example in `pyforge-doctor`'s own tracked ledger.

**Second-run behavior against an unchanged Tier-3 copy (the question left
open for Story 8.4).** Re-running `--fix` against the SAME already-promoted
Tier-3 file (untouched by design -- Never boundary) re-derives the exact
same orphan set every time, since nothing marks an orphan "already
handled" at the Tier-3 layer. This story does not attempt idempotent
re-runs; instead, the existing `summary`-vs-tracked-ledger collision guard
(matrix rows (c)/(d)) transparently catches the re-run as a batch where
every entry's summary now collides with what the FIRST run already wrote,
and aborts with no write -- confirmed live: a second `--fix --project
mason` immediately after a successful promotion reports all 21 entries as
already-tracked collisions, exit 1, tracked ledger byte-identical to its
post-first-run state (no duplicate ids minted, no duplicate content
written). This is a safe, if unfriendly, default: it can never double-write,
but it also cannot distinguish "nothing changed" from "a genuine
collision" in its message. A friendlier "already promoted, nothing to do"
no-op message for the identical-rerun case, and full orphan-level
idempotency across truly incremental runs, is Story 8.4's grandfather
baseline mechanism to solve -- deliberately out of this story's scope.

## Verification

**Commands:**
- `python scripts/deferred_work_promote.py --fix --project doctor` (against a real project with zero live orphans today, per Story 8.1's classifier) -- expected: no-op, exit 0.
- `python -m pytest tests/scripts/test_deferred_work_promote.py -v` -- expected: all pass, including the collision-abort byte-identical assertions.

## Auto Run Result

**Summary.** Added `scripts/deferred_work_promote.py` (`--fix [--project SLUG ...]`), a
standalone mutation script promoting Story 8.1's classified legacy orphans into the tracked
ledger via Story 8.2's `mint_id_for_entry`, mirroring `spec_surface_check.py`'s established
"compute fully in memory, validate, write once" pattern. Doctor's own package is untouched --
this script only imports its pure, read-only helpers.

Adversarial review found this story's biggest risks before landing, not after: Blind Hunter
**reproduced an actual data-loss race** (a concurrent write during the read-validate-write
window was silently destroyed while the run reported success) and, live-verified against real
fleet data, found the script silently dropped a `resolution:` field (present on 13 of 76 real
orphans today) and force-overwrote any orphan's own pre-existing `status:` value. Combined
with Edge Case Hunter's finding that an uncaught I/O error crashed the entire multi-project
run rather than failing just one project, these three plus a crash-safety gap (`write_text`
truncates before completing, unlike a better in-repo precedent already sitting in
`seed_claude_consent.py`) were the four HIGH patches. All four fixed and re-verified: the race
now aborts loudly instead of losing data (reproduced the exact race, confirmed the fix);
writes now go through `tempfile.mkstemp` + `os.replace`; the two live orphans that exposed the
field-dropping bug now promote with their real content intact; and a real unreadable-ancestor
fault in one project's Tier-3 file no longer prevents a clean sibling project from promoting.
Four medium and two low fixes closed the remaining gaps (permission-denied false negatives,
untested mint-failure-mid-batch abort path, blank-summary dedup blind spot, whitespace/casing-
insensitive collision matching, slug-collision detection, a friendlier directory-not-file
error).

**Files changed:**
- `scripts/deferred_work_promote.py` -- new.
- `tests/scripts/test_deferred_work_promote.py` -- new, 26 tests.

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated): 0 intent_gap, 0 bad_spec, 10 patch (4 high / 4 medium / 2 low, all applied and re-verified), 0 defer, 1 reject (a documented-intentional `--project` scope edge case). The content-fidelity finding traced to this story's own intent-contract field list but resolved via exactly one natural reading (preserve extra fields, honor an existing `status:`), not a redesign.

**Follow-up review recommendation:** `true`. This is a mutation script writing to durable, non-regenerable tracked artifacts, and review caught a real, reproduced data-loss bug plus a live-confirmed content-fidelity bug before it ever ran against real data -- exactly the volume and consequence class that warrants an independent follow-up pass before this script is ever run for real against the live 300+-entry fleet-wide backlog.

**Verification performed:** `python -m pytest tests/scripts/test_deferred_work_promote.py -v` -> 26 passed. `pixi run -e pyforge-doctor pyforge-doctor-test` -> 907 passed, 2 skipped (unaffected, confirming the doctor package itself was never touched). All fixes re-verified with real reproductions (the race, the atomic write, live orphan field preservation, sibling-survives-a-crash) rather than synthetic-only tests.

**Residual risks:** Full fuzzy/near-duplicate summary matching (beyond exact + casefold/whitespace-normalized) was explicitly out of scope -- a reworded duplicate could still slip through. The re-read-before-write race guard narrows but does not eliminate the concurrent-write window to zero (true elimination needs OS-level file locking, with no precedent anywhere in this repo); the guard converts the demonstrated failure mode from silent data loss to a loud, safe abort, which is the load-bearing property. This script has never been run against the real, full fleet-wide backlog (only tmp copies) -- that first real run is deliberately not part of this story's own scope.
