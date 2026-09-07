---
title: 'Story 46.1: The adoption register governs wiring'
type: 'chore'
created: '2026-09-07'
baseline_revision: '8d84e2fdb4aa21710bb98c541982a0f94a8dabad'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      The fixture test for the single-station branch checks the
      _claude_md_mentions helper directly rather than driving the real
      top-level `assert not _claude_md_mentions(...)` through an actual
      violation.
    evidence: |-
      Real but low-value: the helper is a one-line substring check, simple
      enough that testing it directly is adequate; a full failure-path drive
      would add test complexity disproportionate to the risk.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::test_single_station_branch_is_not_dead_code
    severity: low
  - summary: >-
      _persona_mentions only scans SKILL.md and customize.toml, not a
      reference/*.md file or README a persona skill might also carry routing
      text in.
    evidence: |-
      Matches this story's own Code Map scope; grepped and confirmed no
      current routing text lives outside those two files for any provisioned
      skill. Revisit if a future persona skill moves routing text elsewhere.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_persona_mentions
    severity: low
  - summary: >-
      No drift guard exists for a currently-skipped § 2 skill prefix becoming
      provisioned later without a corresponding register update.
    evidence: |-
      The test's "not vacuous" assertions (checking bmad-cis-* and skf-* are
      actually exercised) partially cover staleness detection, but a newly
      provisioned prefix with no register-shape change would not be flagged.
      A full drift guard is a larger, separate mechanism than this story's
      scope.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::test_skill_routing_matches_ad2_for_every_currently_provisioned_row
    severity: low
  - summary: >-
      The markdown table parser's cell split on a bare "|" does not handle an
      escaped pipe character inside a cell's text.
    evidence: |-
      Real in principle but currently inert -- no cell in adoption-register.md
      uses an escaped pipe. Not worth the added regex complexity without a
      live case.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_table_rows
    severity: low
  - summary: >-
      _skill_dir_exists's glob matching only recognizes the exact
      "<prefix>-*" wildcard shape via endswith("-*"), not general fnmatch
      semantics.
    evidence: |-
      Currently inert -- every § 2 glob-shaped skill cell uses exactly this
      form. Would need fnmatch (or similar) if the register ever adopts a
      different wildcard convention.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_skill_dir_exists
    severity: low
  - summary: >-
      _persona_mentions and _claude_md_mentions use plain substring matching,
      not word-boundary matching, when checking whether a skill name is
      mentioned.
    evidence: |-
      Real in principle (a skill name that is a substring of an unrelated
      identifier could false-positive or false-negative), but verified no
      current skill name is a substring of anything unrelated in the checked
      files. Deferred rather than adding escaping/regex complexity with no
      live case to justify it.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_persona_mentions
    severity: low
---

<intent-contract>

## Intent

**Problem:** `adoption-register.md` (thirteen bmad-suite members + a § 2 skill-routing table) already exists and its claims were verified live 2026-09-06, but nothing machine-checks that `steward suite pipeline-truth`'s `wired` column still agrees with it, that every routed skill has exactly one wielding persona and is never routed via CLAUDE.md, or that the register's own status cells stay story-key-shaped rather than drifting into free-text state words.

**Approach:** Re-verify the register's `Wired` column against a live `steward suite pipeline-truth --json` run (13/13 agreement or a recorded finding), then ship one new meta-test (`tests/meta/test_adoption_register.py`) encoding the AD-2/AD-6 invariants going forward: for every § 2 skill whose dir currently exists on disk and whose row names a single wielding station, that station's `bmad-agent-<station>` persona skill (SKILL.md or customize.toml) references it and CLAUDE.md never does; for every skill (including multi-station/`all stations` rows), CLAUDE.md never references it either; and every § 1 status/story cell contains no bare lifecycle-status word (`done`, `blocked`, `backlog`, `in-progress`, `ready`) as a whole word.

## Boundaries & Constraints

**Always:**
- Treat `adoption-register.md` as already-authored and settled (verify, not decide) -- do not rewrite its rows, posture-change section, or § 2 assignments.
- Run the real `steward suite pipeline-truth --json` command and compare its per-package `wired.value` against the register's own `Wired 2026-09-06` column category (e.g. `present`, `unwired`, `runnable`, `wired`, `documented`, `n/a`, `provisionable`) -- a register cell's extra parenthetical detail (e.g. `"present, 16 skills"`) is not a disagreement as long as the base category matches.
- The meta-test must be a real, currently-passing pytest test discovered by `pyforge-steward-test` -- not a stub, not marked `xfail`/`skip`.
- For a § 2 row whose Wielding-station cell names exactly ONE station (comma-free, not `all stations`), and whose skill dir(s) currently exist under `.claude/skills/`, assert that station's persona skill (`bmad-agent-<station>/SKILL.md` or `customize.toml`) mentions the skill name, and that `CLAUDE.md` does not.
- For every § 2 row regardless of station count (including `all stations` and multi-station rows like CIS's `herald, scribe`), assert `CLAUDE.md` never mentions the skill name -- this half of AD-2 is unambiguous regardless of station-count shape.
- Word-boundary match the forbidden status words in § 1's last column (`\bdone\b`, `\bblocked\b`, `\bbacklog\b`, `\bin-progress\b`, `\bready\b`, case-insensitive) so a legitimate prose word like "unblocked" is never a false positive.

**Never:**
- Never assert a single-station requirement against a multi-station or `all stations` row -- those shapes are the register's own settled call, not a defect this story adjudicates.
- Never invent or add new skill-routing pointer lines to close a gap the meta-test finds -- if the live tree disagrees with the register (e.g. a skill dir exists but no persona currently references it), record it as a finding in this story's own memlog/spec and exempt that specific row from the test's positive assertion with a one-line comment naming the gap, rather than silently fabricating the missing routing text.
- Never change `steward suite pipeline-truth`'s implementation, `provision.py`, or any persona skill's `SKILL.md` content in this story -- it verifies the register, it does not re-provision or re-route anything.
- Never touch `pipeline-truth`'s installed-stage probe (that is Story 46.9's surface).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Wired-column agreement | Live `steward suite pipeline-truth --json` output vs. register § 1 | 13/13 base-category agreement recorded (in this story's spec/memlog, not asserted by the shipped pytest -- pipeline-truth's live network probes make it unsuitable for an offline CI meta-test) | A disagreement is written up as a named finding, not silently ignored |
| Single-station § 2 row, skill dir present | e.g. skf-* rows if any were single-station (none currently are; exercised via a synthetic single-station fixture row in the test itself if no real one qualifies) | persona skill references it; CLAUDE.md does not | Missing persona reference or a CLAUDE.md hit fails the test with the offending skill name |
| Multi-station / all-stations row (CIS, skf) | `bmad-cis-*`, `skf-*` | Exempted from the single-station assertion; still checked that CLAUDE.md never mentions them | -- |
| Not-yet-provisioned skill named in § 2 (e.g. `bmad-os-*`, `mc-*`) | Skill dir absent from `.claude/skills/` today | Skipped entirely -- this story never asserts against a skill that does not exist yet | -- |
| Status/story cell hygiene | Every non-empty § 1 last-column cell | No bare `done`/`blocked`/`backlog`/`in-progress`/`ready` word | A hit fails the test naming the offending row and word |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- the register itself (§ 1 lines ~9-28, § 2 lines ~30-49). Do not edit its content; read-only source of truth for the new test.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py:754` (`build_pipeline_truth_report`), `:964` (`format_pipeline_truth`) -- the live command backing `steward suite pipeline-truth`. Confirmed live 2026-09-07: 13/13 packages, `wired.value` per package matches the register's base category for every row (see this story's own verification run).
- `.claude/skills/bmad-agent-<station>/SKILL.md` and `customize.toml` for each station (`herald`, `doctor`, `warden`, `scribe`, `marshal`, `steward`, `atlas`, `mason`) -- the persona skills the meta-test greps for a skill-name mention.
- `CLAUDE.md` (repo root) -- must never mention any § 2 skill name; confirmed today it does not mention `bmad-cis` or `skf-` literally (grepped).
- `src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py` -- an existing meta-test in the same directory; follow its `_repo_root()` helper pattern (locate root via `pixi.toml` + `.claude/skills` markers) rather than a hardcoded path.
- `.claude/skills/` -- current on-disk skill inventory. Confirmed today: only `bmad-cis-*` (10 dirs, wielders `herald, scribe` per register, multi-station) and `skf-*` (16 dirs, wielder `all stations` per register) among § 2's rows actually exist; `bmad-os-*`, `bmad-testarch-*`, `mc-*`, and the bmad-builder-derived skills do not exist yet (their provisioning stories are 46.2-46.6, not yet run).
- Live 2026-09-07 finding (grepped before writing this spec): no `bmad-agent-*` persona skill currently mentions `bmad-cis` by name (the register's own "already routed (`herald-pitch`)" annotation does not correspond to any literal text anywhere in the repo outside the register itself). Per this story's own Never clause, this is recorded as a named gap and the CIS row is exempted from the positive single-station assertion (it is multi-station anyway, so it was already exempt from that half) -- the test still asserts CLAUDE.md never mentions it (true today).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- new file -- parses `adoption-register.md`'s § 1 and § 2 markdown tables (a small local parser is fine; no new dependency), and implements: (1) a status-cell hygiene test over every § 1 "Status / story" cell; (2) a skill-routing test over every § 2 row, applying the single-station / multi-station / all-stations / not-yet-provisioned branching described in Boundaries & Constraints.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` -- append a dated `(event)` line recording the live 2026-09-07 `pipeline-truth` re-verification (13/13 base-category agreement) and the CIS routing-text gap finding (named, not silently fixed).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- flip `46-1-the-adoption-register-governs-wiring` to `done` via the project's normal sprint-ledger-sync mechanism once verified.

**Acceptance Criteria:**
- Given a live `steward suite pipeline-truth --json` run, when its 13 packages' `wired.value` are compared against the register's `Wired 2026-09-06` column, then every one agrees at the base-category level (recorded in the memlog), and any disagreement is written up as a named finding rather than silently papered over.
- Given the new meta-test, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it passes and is discovered as a real test (not skipped/xfail).
- Given a § 2 row naming exactly one wielding station and whose skill dir(s) exist on disk, when the meta-test runs, then it fails loudly if that station's persona skill does not mention the skill, or if CLAUDE.md does.
- Given the CIS and skf rows (multi-station / all-stations), when the meta-test runs, then it does not assert a single-station requirement against them, but does assert CLAUDE.md never mentions them.
- Given § 1's "Status / story" column, when the meta-test runs, then no cell contains a bare lifecycle-status word as a whole word (word-boundary matched, so "unblocked" is not a false hit).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 27 findings — high 0, medium 10, low 13, false 4, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: `FORBIDDEN_STATUS_WORDS` omits lifecycle words this repo's own spec convention uses (`draft`, `shipped`, `complete`, `paused`, `superseded`, `in-review`) -- applied: regex extended to include all of them.
  - `[low]` `[patch]` Blind Hunter: § 2 test never asserts `header[2]` ("Wielding station") shape, unlike the § 1 test's `header[-1]` check -- applied: added `assert header[2] == "Wielding station"`.
  - `[low]` `[patch]` Blind Hunter: separator-row filter only matches bare dashes, not colon-aligned (`:---:`) Markdown separators -- applied: regex widened to `r":?-+:?"`.
  - `[medium]` `[patch]` Blind Hunter: `_station_shape`'s `/`-splitting branch is untested; a slash-joined dual-station cell would silently drop the second station -- applied: fixed together with the matching Edge Case Hunter / Verification Gap findings below (same root cause, one change).
  - `[low]` `[defer]` Blind Hunter: the fixture test checks `_claude_md_mentions`'s return value directly but never drives the real top-level `assert not ...` through an actual violation -- real but low-value; the helper is simple enough that direct testing of it is adequate.
  - `[medium]` `[patch]` Blind Hunter: the ledger flip to `done` rests on self-reported memlog prose with no independent/automated verification artifact -- this team's own history flags exactly this pattern as having produced false-dones -- applied: see the new automated test described in the grouped medium finding below (same root cause, same fix).
  - `[low]` `[defer]` Blind Hunter: `_persona_mentions` only scans `SKILL.md`/`customize.toml`, not a `reference/*.md` or README -- matches this story's own Code Map scope; no current routing text lives elsewhere (verified by grep).
  - `[false]` `[reject]` Blind Hunter: the CIS routing-text gap is recorded only in `.memlog.md`, not annotated on the register itself -- refuted: the story's own Never clause explicitly authorizes recording a gap by memlog "rather than silently fabricating the missing routing text"; a register footnote isn't required by anything in scope.
  - `[low]` `[defer]` Blind Hunter: no drift guard against a currently-skipped § 2 prefix becoming provisioned later without a register update -- the test's own "not vacuous" assertions (checking bmad-cis/skf are actually exercised) partially cover this; a full drift guard is a larger, separate mechanism.
  - `[false]` `[reject]` Blind Hunter: nothing confirms the new test file is discovered by `pyforge-steward-test`'s pytest collection -- refuted: directly verified, the full suite's pass count moved from 1104 to 1109 (then 1110 after this pass's own addition), confirming discovery.
  - `[low]` `[patch]` Edge Case Hunter: § 1 `rows[0]` indexed before checking `rows` is non-empty (IndexError instead of a diagnostic if the table becomes fully empty) -- applied: added `assert rows, "no § 1 table rows parsed..."` before indexing.
  - `[low]` `[patch]` Edge Case Hunter: § 2 `rows[0]` indexed before checking `rows` is non-empty -- applied: same fix for § 2.
  - `[low]` `[patch]` Edge Case Hunter: unguarded `next()` for `cis_row`/`skf_row` lookup raises `StopIteration` instead of a clear assertion on register-shape drift -- applied: both now use `next(..., None)` plus an explicit `assert ... is not None` with a diagnostic message.
  - `[low]` `[defer]` Edge Case Hunter: naive `"|"`.split doesn't handle an escaped pipe inside a cell -- real but currently inert (no register cell uses one); not worth speculative complexity.
  - `[low]` `[defer]` Edge Case Hunter: glob matching via `endswith("-*")` rather than `fnmatch` could silently skip a differently-shaped wildcard -- currently inert (every § 2 glob row uses the exact `<prefix>-*` shape); deferred rather than widening matching semantics speculatively.
  - `[medium]` `[patch]` Edge Case Hunter: multi-station cells joined by `;` with no comma left inside any parenthetical would be misclassified as single-station -- applied together with the Verification Gap finding below (same fix: parentheticals stripped first, then `,`/`/`/`;` all treated as multi-station separators).
  - `[low]` `[defer]` Edge Case Hunter: `_persona_mentions`/`_claude_md_mentions` use substring match, not word-boundary -- real in principle, but no current skill name is a substring of an unrelated identifier anywhere in the checked files (verified); deferred rather than adding regex-escaping complexity with no live case to justify it.
  - `[low]` `[patch]` Edge Case Hunter: `FORBIDDEN_STATUS_WORDS` hardcoded to 5 words, missing `draft`/`shipped`/`in-review`/`superseded` -- duplicate of the Blind Hunter status-words finding above; same fix, already applied.
  - `[medium]` `[patch]` Edge Case Hunter (claim): nothing machine-checks that `pipeline-truth`'s wired column still agrees with the register; agreement is only a one-time `.memlog.md` note -- grouped with the Verification Gap finding below; applied via the new automated test.
  - `[medium]` `[patch]` Edge Case Hunter (claim): AD-2's "exactly one wielding persona" is not actually verified -- the test only asserted the named station's persona mentions the skill, never that other personas omit it -- applied: added `_other_personas_silent`, iterating all eight station personas and asserting none but the named one mentions a single-station skill.
  - `[medium]` `[patch]` Verification Gap (pre-verified gap finding, trusted per protocol): the register-agrees-with-pipeline-truth AC (this story's own headline Given/When/Then) had no automated verification -- confirmed by actually running the test suite and grepping the repo; no test anywhere compared the register to `build_pipeline_truth_report`'s live output. Action: added `test_wired_column_agrees_with_live_pipeline_truth_for_every_row`, calling the real `build_pipeline_truth_report` with `ProbeHooks` stubbing every network-touching stage (npm/github/channel/recipe/installed) and leaving `wired` as the real, local, offline-safe default probe -- asserts all 13 rows' live `wired.value` matches the register's base category. Passes today; will fail loudly the moment either drifts.
  - `[medium]` `[patch]` Verification Gap (other finding): `_station_shape`'s comma-only multi-station detection misclassifies the real `eval-quality` row (`"warden / marshal"`, no comma) as single-station `"warden"`, silently dropping `marshal` -- currently inert only because `eval-quality` has no on-disk skill dir yet. Action: `_station_shape` now strips parenthetical content first, then treats `,`, `/`, or `;` as each indicating multi-station -- re-verified the TEA row (`"marshal (workflows, review lens); warden (advisory)"`) still classifies as multi, now correctly via the semicolon rather than by accident via a comma inside one station's own parenthetical.
  - `[medium]` `[patch]` Intent Alignment: Reading B (the ongoing-invariant reading of the AC) is not implemented -- no code in the diff called `steward suite pipeline-truth` or its underlying report builder; the 13/13 claim was attested only by dated prose -- same root cause as the Verification Gap finding above; resolved by the same new test.
  - `[medium]` `[patch]` Intent Alignment: Reading C -- AD-2's own settled call ("AGENTS.md holds one pointer line to this table") corresponds to no literal text anywhere in the repo; `bmad-agent-steward`, `AGENTS.md`, and every other persona skill were grepped and none mentions "adoption register" / "adoption-register" -- a real, in-scope gap (the story's own Surface line names `bmad-agent-steward` skill as a "routing-note home decision" surface). Action: added one pointer line to `AGENTS.md` § "Where things are" naming the register and citing AD-2, per the story's own settled convention (one line, not per-skill).
  - `[false]` `[reject]` Intent Alignment: Reading C -- the other two named memlog surfaces (`spec-bmad-suite-channel-product`, `spec-bmad-611-era-alignment`) look untouched by this diff -- refuted by the auditor's own investigation: `spec-bmad-suite-channel-product/.memlog.md` already carries the required superseding entry, dated before this diff, from prior work -- pre-satisfied, not a gap in this change.
  - `[false]` `[reject]` Intent Alignment: `adoption-register.md` itself is not modified by this diff -- refuted: correct behavior under "verify, not decide" when no member's verdict/wielder/provisioning path actually changed; the diff's own memlog entry states the 13/13 re-verification found zero disagreements, which is exactly the condition under which no row should change.
  - `[medium]` `[patch]` Intent Alignment: Reading D -- the ledger flip certifies the story's whole Surface + Given/When/Then, but the diff's only durable, re-checkable artifact was the AD-2/AD-6 self-consistency test, not a durable check on the register's agreement with the live tool or the AGENTS-pointer-line half of AD-2 -- same root cause as the two medium findings above (pipeline-truth test, AGENTS.md line); both now applied close this gap.

## Design Notes

The register's own § 2 rows mix three shapes the test must branch on: (a) single-station rows (none currently instantiate this branch with an on-disk skill, since every currently-provisioned row is either multi-station or all-stations -- the branch is still implemented and exercised by a small in-test synthetic fixture so it is not dead code), (b) multi-station rows (CIS: `herald, scribe`), (c) `all stations` rows (skf). Only (a) gets the full "exactly one persona references it" assertion; (b) and (c) only get the "CLAUDE.md never" half, since AD-2's "one wielding station" framing does not apply to a row the register itself declared multi-station or blanket.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all pass, including the new `test_adoption_register.py`.
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward suite pipeline-truth --json` -- expected: 13 packages; manually diff each `wired.value` against the register's `Wired 2026-09-06` column (documented in this story's memlog entry, not asserted by CI).
- `grep -c "bmad-cis\|skf-" CLAUDE.md` -- expected: 0.

## Auto Run Result

Status: done

**Summary:** Shipped the AD-2/AD-6 meta-test (`tests/meta/test_adoption_register.py`) verifying the adoption register's status-cell hygiene and skill-routing invariants, re-verified `steward suite pipeline-truth`'s 13/13 base-category agreement with the register live, and closed a real gap this review pass found: no automated check actually asserted that agreement going forward (only a one-time memlog note did), and the AD-2 "AGENTS.md holds one pointer line" convention had no line anywhere in the repo. Both are now fixed with real, passing, durable assertions rather than left as prose claims.

**Files changed:**
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` (new, then patched this pass) -- 6 tests: § 1 status-cell hygiene (2), § 2 AD-2 routing including the "exactly one" negative check (1), multi/all-station exemption (1), a live pipeline-truth-vs-register agreement test using stubbed network hooks (1), and the single-station branch fixture (1).
- `AGENTS.md` -- one new pointer line under "Where things are" naming `adoption-register.md` § 2 as the durable home for bmad-suite skill wiring (AD-2).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` -- two dated entries: the live 2026-09-07 pipeline-truth re-verification, and the named CIS routing-text gap.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- `46-1` flipped to `done` (via the project's sprint-ledger-sync mechanism, re-run to also reconcile a transient drift observed mid-session between the Tier-3 feed and the tracked ledger -- see Residual risks).

**Review findings breakdown** (this pass, 27 findings from 4 independent context-free reviewers -- Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (10 medium-verdict findings, several sharing one fix; distinct code changes: extended `FORBIDDEN_STATUS_WORDS`, added `header[2]` shape assertion, widened the separator-row regex, guarded `next()`/empty-`rows` indexing with clear diagnostics, fixed `_station_shape` to treat `,`/`/`/`;` as multi-station after stripping parentheticals, added the AD-2 "exactly one" negative check, added the live pipeline-truth-vs-register agreement test, added the AGENTS.md pointer line).
- Deferred (6, recorded in frontmatter `deferred:`): the fixture test's failure-path coverage, `_persona_mentions`'s file-scope limit, no drift guard for newly-provisioned skip-path prefixes, escaped-pipe parsing, `fnmatch`-vs-`endswith` glob matching, substring-vs-word-boundary matching -- all real in principle, all currently inert (verified against the live register/skill tree), none worth speculative complexity today.
- Rejected (4 false): the CIS routing-text gap being memlog-only (explicitly authorized by this story's own Never clause); pytest-discovery doubt (directly refuted -- suite pass count moved 1104 to 1110); the other two named memlog surfaces looking untouched (pre-satisfied by prior commits, verified); the register itself not being edited (correct "verify, not decide" behavior when zero disagreements were found).

**Process note:** mid-session, `git diff`/`git status` and direct file reads (`cat`/`grep`/`python3`) of `sprint-status-ledger.yaml` disagreed with each other transiently (git reported a pending single-line change that repeated `cat`/`grep`/`python3` reads did not show, and vice versa for an unrelated key). No external process or leftover subagent was found to explain it (`ps aux` showed only this session's own `claude` process; the one previously-launched investigation-only subagent that had gone out of scope was independently confirmed already stopped via `TaskStop`, returning "no task found"). Re-running `sprint-ledger-sync` from the (independently confirmed correct) Tier-3 source and re-checking via `git diff`/`git show` resolved it to a single, clean, correct 1-line diff, which is what's committed. Flagging as environment-level flakiness worth a second look, not a data-integrity defect in this story's own artifacts.

**Follow-up review recommendation: true.** Ten medium-verdict findings were patched this pass, several touching the same parsing helpers (`_station_shape`, `_table_rows`) in quick succession. Specific unverified risk to re-check: confirm the `_station_shape` rewrite (parentheses-stripped-then-separator-check) doesn't misclassify any § 2 row shape not currently present in the register (only the existing rows -- CIS multi, skf all-stations, TEA semicolon-multi, eval-quality slash-multi -- were exercised); and confirm the new live pipeline-truth test stays fast/offline-safe as `SUITE_PACKAGES` grows in future stories (each new package's `wired` probe must stay local-only for the stubbed-hooks approach to remain valid).

**Verification performed:** `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py -v` (6/6 passed, before and after each patch); `pixi run -e pyforge-steward pyforge-steward-test` (1104 -> 1109 -> 1110 passed across the implementation and this review pass, confirming new-test discovery each time); manually re-verified `_station_shape` against all four real § 2 station-cell shapes (`"herald, scribe"` -> multi, `"all stations"` -> all, `"herald (studio only)"` -> single/herald, `"warden / marshal"` -> now correctly multi, `"marshal (workflows, review lens); warden (advisory)"` -> multi via the semicolon); confirmed `AGENTS.md`'s new line via direct read; confirmed via `git diff`/`git show HEAD` that the final ledger diff is exactly the intended single-line `46-1: backlog -> done` change with no unrelated drift.

**Residual risks:** the transient git/file-read disagreement noted above (process note) resolved cleanly but its root cause in this environment is unconfirmed. The two remaining named "Reading C" gaps from the Intent Alignment audit that this pass did NOT address: the other two named memlog surfaces (verified pre-satisfied, no action needed) and the register itself (verified correctly untouched) -- both closed as false findings, not residual risk. The six deferred items above are real-in-principle, currently-inert fragility in the new test's parsing helpers.
