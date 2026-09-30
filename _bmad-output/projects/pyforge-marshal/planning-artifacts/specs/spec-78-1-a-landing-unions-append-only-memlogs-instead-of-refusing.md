---
title: '78.1: A landing unions append-only memlogs instead of refusing'
type: 'feature'
created: '2026-09-30'
status: 'done'
baseline_revision: '70d6e11a515a75838b7d6c5c9a5e24a96641204d'
flag-exempt: detector-or-gate   # the heal decides whether a landing merges: part of marshal's landing gate (spec-feature-flag-governance Q2; Story 74.2's precedent)
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-59-1-a-ledger-only-conflict-is-healed-by-a-merge-of-origin-main-not-a-union-commit.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - _bmad/scripts/memlog.py
deferred:
  - summary: >-
      The heal reads refs/remotes/origin/main by name for its texts and conflict paths, then merge_ref_resolving resolves it again, so a concurrent fetch between the two makes a resolution stale.
    evidence: |-
      Pre-existing since Story 59.1 (CAP-269): the ledger heal has always read the probe ref by name and merged it afterwards. A stale resolution would overwrite entries main gained in a conflicted memlog or ledger. Pinning the ref to a sha needs resolve_ref (a branch-name taker, refused for a full ref by tests/meta/test_local_branch_refs_are_full_refnames.py) or a new VcsPort method, which Story 78.1's Never list forbids. Settling it: a story that pins the probe to a sha once and passes it to the reads, merge_tree_conflict_paths and merge_ref_resolving.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** when a landing's forge merge fails, `dispatch land` runs `try_heal_dispatch_land_merge`
(`dispatch_land_heal.py`, CAP-4 / CAP-269). It measures conflicts against `refs/remotes/origin/main` and resolves exactly
one path mechanically, the landing project's own sprint ledger (`core/dispatch_landing.py::unknown_conflict_paths`).
Every other conflicted path escalates, and the landing is refused (MRS-DISP-038).

Every story's surface reconcile appends entries to Spec `.memlog.md` files: its own Spec's, and the co-governors'
(`spec-pyforge-core`, `spec-pyforge-unifying-strategy`). When two stories run at once, both append to the same memlogs,
and each append rewrites the frontmatter's `updated:`. The second to land conflicts on those files and is refused,
however clean its code. On 2026-09-30 that refused steward 74.1 (#1679), doctor 35.1 (#1682), steward 76.1 (#1683) and
doctor 36.2 (#1692, twice). Every one was landed by hand.

**Approach:** a conflicted `.memlog.md` joins the mechanical set when both sides only appended to it since the merge
base.

- A pure resolver in `core/dispatch_landing.py` takes the base, `main` and branch texts. It parses each the way
  `_bmad/scripts/memlog.py` writes them: a `---` frontmatter of `key: value` lines, then a body of lines.
  - If either side's body does not start with the base body line for line, the path is not append-only: return no
    resolution.
  - Otherwise the result body is `main`'s body, then each line the branch appended after the base, in order, skipping
    any line `main` already appended.
  - Frontmatter: `main`'s fields in `main`'s order. A field only the branch changed takes the branch's value.
    `updated:` takes the later stamp (ISO text compares correctly). Any other field both sides changed differently
    returns no resolution.
  - Render in `memlog.py`'s shape: `---`, the fields, `---`, a blank line, the body, one trailing newline.
- A classifier names a path a memlog when its basename is `.memlog.md`, in any project: co-governor memlogs live under
  other projects, and an append-only union is safe wherever it sits.
- `try_heal_dispatch_land_merge` stops escalating memlog paths up front. It reads the three texts through
  `VcsPort.file_text_at_ref`, as the ledger heal does, and resolves every conflicted memlog. Any memlog with no
  resolution escalates by name. The ledger's resolution and every memlog's go into the one `merge_ref_resolving` map, so
  one real merge of `origin/main` heals them all. Any other path still aborts that merge before a commit or push.
- `dispatch_land.py` records the healed memlog paths in the landing's data beside `ledger_union_heal`.

Ledger key: `78-1-a-landing-unions-append-only-memlogs-instead-of-refusing`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-283 (FR-230), which extends CAP-269 (FR-215) for this one path class.
- `spec-feature-flag-governance` Q2: `flag-exempt: detector-or-gate`. The heal decides whether a landing merges.

## Acceptance Criteria

- Given base, `main` and branch memlog texts where both sides appended entries and restamped `updated:` When the resolver runs Then it returns `main`'s frontmatter with the later `updated:`, `main`'s body, then the branch's appended lines in order, with no line twice
- Given a branch whose body rewrote, dropped or reordered a base line (or `main`'s did) When the resolver runs Then it returns no resolution
- Given a `topic:` (or any field other than `updated:`) both sides changed to different values When the resolver runs Then it returns no resolution; a field only one side changed takes that side's value
- Given a line both sides appended When the resolver runs Then it appears once, in `main`'s position
- Given a dispatch branch and `origin/main` in a bare-remote fixture whose only conflicts are two `.memlog.md` files both appended to When `dispatch land`'s heal runs Then the pushed head is a merge commit whose second parent is `origin/main`, each memlog holds every entry once, and the retried forge merge succeeds
- Given memlog and ledger conflicts together When the heal runs Then both resolve in the same merge commit
- Given a memlog with no resolution, or a memlog plus any other conflicted file When the heal runs Then the landing escalates naming the unresolved path, with nothing committed or pushed
- Given a healed landing When its record is written Then it names the healed memlog paths
- Given the memlog branch removed from the classifier When the bare-remote test runs Then it fails (mutation)

## Tasks

1. Read `dispatch_land_heal.py`, `core/dispatch_landing.py`'s ledger helpers, `ports/vcs.py::merge_ref_resolving`, and
   Story 59.1's heal tests in `tests/unit/test_dispatch_landing.py` (their bare-remote and forge-fake fixtures).
2. Add the pure resolver and the memlog classifier to `core/dispatch_landing.py`, with a table test covering every
   criterion above that names the resolver.
3. Rework the heal so the ledger and every conflicted memlog resolve into one `merge_ref_resolving` map; an unresolved
   memlog escalates by name.
4. Record the healed paths in `dispatch_land.py`'s landing data.
5. Add bare-remote heal tests beside Story 59.1's: memlogs only, memlogs plus ledger, an edited memlog, a memlog plus
   another file. Run the mutation by hand.
6. Run both `verify_commands`, then reconcile every Spec `spec-surface-check` names for the changed files: memlog first,
   `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep every entry from both sides, none twice. A resolution never drops a line to make a merge clean.
- Keep CAP-269's guarantees: the probe is `refs/remotes/origin/main`, one unresolvable path aborts the merge before any
  commit or push, a refused retry leaves remote `main` untouched.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not add any other file class to the mechanical set: not `scripts/.spec-surface-baseline.json`, not another
  project's ledger.
- Do not add a `VcsPort` method or change `merge_ref_resolving`'s contract.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| both appended | base + 2 on main, base + 1 on branch | main's body + the branch's line; later `updated:` | — |
| one side appended | only the branch appended | the branch's text; `updated:` the branch's | — |
| same line both sides | identical appended line | appears once | — |
| rewritten base line | branch edits an existing entry | no resolution | escalate by name |
| truncated body | a side drops trailing base lines | no resolution | escalate by name |
| other field both sides | `topic:` differs on both | no resolution | escalate by name |
| no frontmatter | a text without `---` | no resolution | escalate by name |
| memlog + ledger | both conflicted | one merge resolves both | — |
| memlog + other file | e.g. a `.py` file | — | escalate the other file, nothing committed |

</intent-contract>

## Code Map

Investigated 2026-09-30 (step 2). Paths are under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/core/dispatch_landing.py` -- pure home of the ledger helpers (`three_way_ledger_statuses`, `is_mechanical_conflict_path`, `unknown_conflict_paths`). Add `MEMLOG_BASENAME`, `is_memlog_path`, and the resolver `union_memlog_texts(base, main, branch) -> str | None` here. `core/` may not import `adapters` (AD-4), and `_bmad/scripts/memlog.py` is a script outside the package: mirror its `split` (first line `---`, closing fence the first later line that is exactly `---`, `key: value` lines split on the first `:` and stripped, body `lstrip("\n")`) and `render` (`---\n<fields>\n---\n\n<body rstripped>\n`) in the resolver; do not import it.
- `src/pyforge/marshal/dispatch_land_heal.py` -- `try_heal_dispatch_land_merge` (line 47) computes `unknown = unknown_conflict_paths(conflict_paths, ...)` up front and only enters the union heal when every conflicted path is the ledger. `_try_ledger_union_heal` (line 131) reads base/main/branch ledger text with `vcs.file_text_at_ref(git_repo_root, base_sha | probe | head_ref, rel)`, then one `vcs.merge_ref_resolving(worktree, probe, resolutions={ledger_rel: resolved}, message=...)`, `push`, retried `forge.merge_pr`. Rework: drop memlog paths from the `unknown` set, resolve the ledger only when it conflicted, resolve every conflicted memlog, and put all of them in the one `resolutions` map. `DispatchLandHealResult` gains `healed_memlog_paths: tuple[str, ...] = ()` (defaulted, so Story 59.1's `DispatchLandHealResult(healed=True, retried_forge_merge=True)` assertions still hold for a ledger-only heal).
- `src/pyforge/marshal/adapters/vcs_git.py:1171` -- `merge_ref_resolving` (read-only here, contract unchanged). It writes only the paths git left conflicted and ignores extra `resolutions` keys; a conflicted path with no resolution aborts the merge before any commit.
- `src/pyforge/marshal/dispatch_land.py:972-1043` -- the heal call and the landing record: `data["ledger_union_heal"] = True` when `heal.retried_forge_merge`. Add `data["memlog_union_heal"]` (the healed paths, as a list) beside it when non-empty. `ledger_union_heal` keeps its meaning "the union merge ran"; only `tests/unit/test_dispatch_landing.py:1129` reads it.
- `tests/meta/test_local_branch_refs_are_full_refnames.py` -- AST scan that every `vcs.file_text_at_ref` ref is a full ref or sha; keep the heal's variable names `probe`, `head_ref`, `base_sha` so the new reads stay inside it.
- `tests/unit/test_dispatch_land_heal.py:350-600` -- Story 59.1's bare-remote fixtures (`_landing`, `_HonestForge`, `_heal`, `_generated_ledger`). Task 1 names `tests/unit/test_dispatch_landing.py`; the heal fixtures are here, and `test_dispatch_landing.py:1129` is the landing-record test. Add the resolver table test and the bare-remote memlog tests in this file; add the record test beside line 1129.
- `_bmad/scripts/memlog.py:90-113` -- the file shape the resolver parses and renders.

## Binding

Parent capability: `spec-pyforge-marshal` CAP-283 (FR-230).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-09-30 entry.
Ledger key: `78-1-a-landing-unions-append-only-memlogs-instead-of-refusing`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none; `flag-exempt: detector-or-gate`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- The mutation in Task 5 — expected: the bare-remote memlog test fails with the classifier's memlog branch removed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

### 2026-09-30 — Review pass
- verdicts: 30 findings — high 0, medium 5, low 19, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind Hunter: the per-line dedup of the branch's appended lines against `main`'s can drop a blank or continuation line of a multi-line entry — real for hand-written multi-line appends (three layers reproduced it with synthetic input), but the path production takes cannot reach it: `memlog.py append` writes one-line entries (`" ".join(args.text.split())`), the marshal memlog's lines 1282-1601 are all single-line entries, and the dedup only reads lines appended since the merge base. The intent-contract's own I/O matrix row says an identical appended line appears once, and no unique text is lost. Rejected: the fix (entry-level grouping, or escalating on a skipped non-entry line) adds a branch and changes the contract's stated rule. Grouped root cause with the four rows below.
  - `[medium]` `[patch]` Blind Hunter: the two scoped `--write-baseline` stamps rewrote `scripts/.spec-surface-baseline.json` hashes for files this change never touched (`pixi.toml`, `scripts/fleet_scan.py`, `adapters/vcs_git.py`, `cli/land.py`, core `flags.py`, steward `cutover.py` and others) — verified in the diff, and this run's invocation forbids a producer passing `--write-baseline` (the stamp is the parent's, as Story 65.1's memlog entry says). Patched: `scripts/.spec-surface-baseline.json` restored from `baseline_revision` (0 diff lines); `spec_surface_reconcile.py` and `spec-surface-check` both still exit 0 without it. Grouped with the two rows marked "baseline".
  - `[low]` `[patch]` Blind Hunter: a git read failure while resolving is "silent and untested" — the silent half is refuted (`dispatch_land.py` emits MRS-DISP-020 with the failure text when `escalated_paths` is empty, exactly as the pre-change ledger read did), the untested half is real. Patched with the read-failure test (see the Verification Gap row).
  - `[low]` `[reject]` Blind Hunter: an unresolved memlog is reported through MRS-DISP-038's "unknown conflict path" text with no reason — the path is named as the intent requires; a per-path reason is new plumbing beyond the contract, and the operator's next step (read the file's diff) is the same either way.
  - `[low]` `[reject]` Blind Hunter: memlog and ledger text reads run before the cheap short-circuit when another path is already unknown — a few local `git show` calls on a landing that is being refused; short-circuiting would stop the escalation from naming an unresolved memlog beside the other file, which `test_real_heal_names_both_the_other_file_and_the_edited_memlog` pins.
  - `[low]` `[reject]` Blind Hunter: two memlog decision points that can diverge, a redundant `all(...)` guard, and derivable `has_ledger`/`has_memlogs` — `is_memlog_path` normalises `\` itself so the two sites agree; the `all(...)` guard is unchanged from Story 59.1 (already redundant then) and harmless; the two booleans only build the commit message. No named harm.
  - `[false]` `[reject]` Blind Hunter: `is_memlog_path` is broader than "Spec memlog" — the intent-contract requires exactly this: a basename of `.memlog.md` "in any project ... an append-only union is safe wherever it sits".
  - `[low]` `[reject]` Blind Hunter: the whole-file re-render normalises frontmatter (drops colon-less lines, collapses duplicate keys, CRLF to LF) — it mirrors `memlog.py`'s own `split`/`render`, which every real append already applies; 234 of the 237 tracked memlogs round-trip and the rest escalate or lose one trailing blank line under `archive/`.
  - `[low]` `[reject]` Blind Hunter: test gaps (no modify/delete case, no multi-line case, one idempotence input, a fake that falls through on an unknown ref, mutation recorded as prose) — a modify/delete reads as `""`, has no frontmatter and escalates (I/O matrix row "no frontmatter"); the fake's final-text assertions fail on a wrong base ref; the mutation is a by-hand check by the spec's own Task 5 and was re-run in this pass (see Auto Run Result).
  - `[low]` `[reject]` Blind Hunter: `ledger_union_heal` is set for a memlog-only heal — the key keeps its meaning "the union merge ran"; `memlog_union_heal` beside it names the memlog paths, so the record is unambiguous, and nothing but one test reads either key. Grouped with the Edge Case Hunter row on the same claim.
  - `[false]` `[reject]` Blind Hunter: the story spec lacks completion evidence — the evidence is written under `## Auto Run Result` at Finalize in this same step.
  - `[low]` `[patch]` Blind Hunter: stale wording (the first docstring line of `try_heal_dispatch_land_merge`) and no CAP-283 row in the flag inventory — the docstring is patched to name the memlog union; the flag inventory is a report (Story 34.4), not a detector, and regenerates with `flag-inventory`, so no row is required for this change; MRS-DISP-038's text stays as is (see the message row above).
  - `[low]` `[reject]` Edge Case Hunter: multi-line dedup drops a branch's continuation or blank line — same root cause and same evidence as the first row above.
  - `[low]` `[reject]` Edge Case Hunter: U+2028, NEL, form feed or a colon-less frontmatter line in a memlog is mutated by the re-render — `memlog.py` applies the same `splitlines()` and drops the same lines on every append, and no tracked memlog carries them; see the re-render row above.
  - `[medium]` `[defer]` Edge Case Hunter: `refs/remotes/origin/main` is read by name (texts, conflict paths) and then resolved again by `merge_ref_resolving`; a concurrent `git fetch` between them makes the resolution stale and could overwrite entries `main` gained — real by construction and pre-existing (Story 59.1's ledger heal reads and merges the probe ref the same way); pinning the ref to a sha needs `resolve_ref` (a branch-name taker) or a new `VcsPort` method, which this story forbids. Recorded under `deferred`.
  - `[medium]` `[patch]` Edge Case Hunter: the text reads now run before `forge.pr_merge_state` (a network call), widening the read-to-merge window of the row above — verified in the diff: the old ledger reads ran after it. Patched: `pr_merge_state` moved above the resolution block in `try_heal_dispatch_land_merge`, so the window is what Story 59.1 left it.
  - `[low]` `[reject]` Edge Case Hunter: resolve before the unknown-path short-circuit — same claim and evidence as the Blind Hunter short-circuit row.
  - `[low]` `[reject]` Edge Case Hunter: an unresolved memlog carries no reason into the finding — same claim and evidence as the Blind Hunter message row.
  - `[low]` `[reject]` Edge Case Hunter: `ledger_union_heal` set when only memlogs were unioned — same claim and evidence as the Blind Hunter row on that key.
  - `[low]` `[reject]` Edge Case Hunter (claim): the boundary "never drops a line" is broken by the dedup — same root cause and evidence as the first row: the skipped line is present once in the result, in `main`'s position.
  - `[low]` `[patch]` Verification Gap: a heal whose merge-base or text read raises `VcsCommandError` has no test — the block was moved and now covers memlog reads. Patched: `test_heal_refuses_cleanly_when_a_resolution_read_fails` (six cases: memlog, ledger and both, each failing on `merge_base` and on `file_text_at_ref`) asserts `healed=False`, nothing merged, committed or pushed, and the forge never asked to merge.
  - `[low]` `[reject]` Verification Gap (other findings): multi-line dedup — same root cause and evidence as the first row.
  - `[medium]` `[patch]` Verification Gap (other findings): the baseline re-stamp covers drift this diff did not cause — baseline; same claim, evidence and fix as the second row.
  - `[false]` `[reject]` Verification Gap (other findings): three tracked memlogs have no frontmatter and cannot be unioned — the reviewer itself marks this "not a defect"; escalating a text with no frontmatter is the specified behaviour (I/O matrix row "no frontmatter").
  - `[false]` `[reject]` Intent Alignment: the bare-remote criterion is tested at the heal, not through `execute_dispatch_land` — the criterion names "`dispatch land`'s heal"; the heal is exercised over a real bare remote and the real `GitVcs`.
  - `[false]` `[reject]` Intent Alignment: the record criterion runs on fakes while the heal criterion runs on real git — the criterion is about the landing record's content, the same fixture family as the existing `ledger_union_heal` record test.
  - `[low]` `[reject]` Intent Alignment: resolver and heal fixtures use single-line entries while the real marshal memlog has multi-line history — same root cause and evidence as the first row.
  - `[false]` `[reject]` Intent Alignment: the mutation criterion is a by-hand run, not a test — Task 5 specifies it by hand; re-run in this pass at both memlog decision sites (see Auto Run Result).
  - `[low]` `[reject]` Intent Alignment: a read failure escalates via MRS-DISP-020, not by name — the pre-change ledger read failure behaved the same; git itself failing has no memlog to name; the new test pins the refusal.
  - `[medium]` `[patch]` Intent Alignment: the baseline JSON is in the diff with hashes of files this change does not touch — baseline; same claim, evidence and fix as the second row.

## Auto Run Result

Status: done

**Summary.** A conflicted `.memlog.md` now joins the landing heal's mechanical set when both sides only appended to it since the merge base. `union_memlog_texts` (pure, in `core/dispatch_landing.py`) returns `main`'s frontmatter with the later `updated:` and `main`'s body followed by the branch's appended lines, or no resolution for a rewritten, dropped or reordered base line, a field both sides changed differently, or a text with no frontmatter. `try_heal_dispatch_land_merge` resolves the ledger and every conflicted memlog into the one `merge_ref_resolving` map, so one real merge of `origin/main` heals them all; an unresolved memlog escalates by name beside any other conflicted path, with nothing committed or pushed. `dispatch land` records the healed paths as `memlog_union_heal`.

**Files changed** (under `src/shared/packages/pyforge-marshal/` unless noted):
- `src/pyforge/marshal/core/dispatch_landing.py` -- `MEMLOG_BASENAME`, `is_memlog_path`, the memlog branch of `is_mechanical_conflict_path`, and the resolver with its `memlog.py`-shaped split and render.
- `src/pyforge/marshal/dispatch_land_heal.py` -- one resolution map for the ledger and every memlog; `DispatchLandHealResult.healed_memlog_paths`; `_try_ledger_union_heal` is now `_try_union_heal`; the forge's merge state is read before the text reads.
- `src/pyforge/marshal/dispatch_land.py` -- records `memlog_union_heal` beside `ledger_union_heal`.
- `tests/unit/test_dispatch_land_heal.py` -- classifier tests, a 23-case resolver table, bare-remote heal tests (memlogs only, a line both sides appended, memlogs plus ledger, a co-governor memlog alone, an edited memlog, a memlog added on both sides, a memlog beside another file, a forge refusal) and the read-failure test.
- `tests/unit/test_dispatch_landing.py` -- the landing-record tests, with and without memlogs.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `.../spec-pyforge-core/.memlog.md` -- the surface reconcile entries naming every governed path changed (two entries each: the implementation and the review patches).

**Review breakdown.** 30 findings: high 0, medium 5, low 19, false 6.
- Patched (4 entries): the baseline stamp reverted to `baseline_revision` (medium; three rows); `pr_merge_state` read before the text reads so the read-to-merge window is not widened (medium); the read-failure test (low; two rows); the stale docstring line (low).
- Deferred (1): the pre-existing probe-ref race, recorded under `deferred` with its location.
- Rejected, with the reasons in the Review Triage Log: per-line dedup of multi-line hand-written entries (`memlog.py append` writes one-line entries, the marshal memlog's tail is all single-line, no unique text is lost, and the fix changes the contract's stated rule; low, six rows); no reason on an unresolved-memlog escalation, work before the short-circuit, two decision points and derivable booleans, re-render normalisation, test-gap nits, `ledger_union_heal` on a memlog-only heal, and a read failure not escalating by name (all low); six `false` rows refuted on the intent-contract's own text or the code (basename rule, completion evidence at Finalize, the criterion's named surface, the by-hand mutation, the frontmatter-less memlogs the reviewer itself called not a defect).

**Follow-up review recommended: true.** Two medium entries were patched on this first pass. The unverified risks: (1) the reorder of `pr_merge_state` restores Story 59.1's read-to-merge window but no unit test can exercise a concurrent `git fetch` inside it; (2) the scoped `--write-baseline` stamps were deliberately not written (this dispatch forbids a producer stamping its own baseline), so `scripts/.spec-surface-baseline.json` still holds the pre-story hashes and the stamp is the parent's, after `git add`, from a clean tree. Patched counts by verdict: medium 2, low 2.

**Verification performed** (each verdict read from an exit code written to a file, never a pipe, from this worktree's own `pyforge-marshal` env):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 9107 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `pixi run -e pyforge-guild lint-types` -- exit 0.
- `pixi run -e pyforge-guild spec-surface-check` -- exit 0; `python scripts/spec_surface_reconcile.py` -- exit 0. Both hold with the baseline JSON at `baseline_revision`.
- Mutation, by hand, re-run in this pass: removing the memlog branch from `is_mechanical_conflict_path` fails 12 tests (including the bare-remote memlog heals); making `is_memlog_path` always false fails 13. `dispatch_landing.py` restored byte-identical to its backup.
- I/O matrix audit: every row is covered by a test that ran and passed -- both appended, one side appended, same line both sides, rewritten base line, truncated body, other field both sides, no frontmatter (resolver table); memlog plus ledger and memlog plus another file (bare-remote heals).
- `pr-preflight` was not run to completion: the subagent's run stopped at `detectors-ci` on `ledger-direction` (steward 77.1 landed on `origin/main` after this branch's base), which clears once this branch merges `origin/main`. The station suites, the touched-module coverage floor and lint were run by hand instead.

**Residual risks.**
- The deferred probe-ref race above (pre-existing; rare).
- Hand-written multi-line entries appended concurrently by both stories with identical continuation or blank lines lose the branch's copy of those lines to `main`'s (policy routes every append through `memlog.py`, which writes one line).
- `scripts/.spec-surface-baseline.json` is unstamped: the operator's or parent's scoped `--write-baseline --spec pyforge-marshal/spec-pyforge-marshal` and `--spec pyforge-marshal/spec-pyforge-core`, after `git add`, from a clean tree, closes it.
- `ledger_union_heal` reads true for a memlog-only heal; `memlog_union_heal` names the paths.
