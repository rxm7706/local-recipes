---
title: "A gate binds to the spec's Success signal"
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '88f2e3bf33b136b8d6e43d2b89e4ab08c4eb07f9'
---

<intent-contract>

## Intent

**Problem:** `marshal gate evaluate` runs whatever `EffectivePolicy.verify_commands` currently names, with no check against what a story's own tracked spec promised as its Success signal when it was written. A test quietly narrowed or removed from policy after a spec was tracked passes silently — the gate reports green while the contract the spec actually made has been broken.

**Approach:** every promoted story spec's own `## Verification` → `**Commands:**` section is a machine-parseable Success signal (verified live: this exact shape is what every spec authored this session — 3.7, 3.8, 2.3, 4.1 — already carries). `core/spec_binding.py` parses it; `core/gate.py::check_spec_binding` confirms every declared command is still among the commands the current run actually executes, folding a mismatch into the same closed admission lattice (AD-31) every other criterion uses — never a side warning that leaves an otherwise-green verdict green.

## Boundaries & Constraints

**Always:**
- `core/spec_binding.py::parse_success_signal(spec_text: str) -> tuple[str, ...] | None` is pure (AD-4). Locates the `## Verification` heading, then the `**Commands:**` sub-list immediately under it, and extracts the single backtick-quoted command from each bullet (`` - `<command>` — expected: ... ``, the exact shape every spec in `planning-artifacts/specs/` already uses — verified against `spec-2-3-*.md`/`spec-4-1-*.md` live, not assumed). Returns `None` when no `## Verification` section exists at all (distinct from an empty tuple, mirroring Story 2.3's own "no declared surface" vs. "declared empty surface" discipline) — `None` means "nothing to bind against," not "bound to nothing."
- `core/gate.py::check_spec_binding(declared_commands: tuple[str, ...] | None, policy_commands: tuple[str, ...]) -> tuple[Finding, ...]` is pure. `declared_commands is None` (no tracked spec, or a tracked spec with no parseable Success signal) → one registered `Finding` naming the missing binding (AC2: "reported explicitly as a finding, never evaluated silently against nothing"). Otherwise, for every command in `declared_commands` NOT present (exact string match) in `policy_commands` → one `Finding` naming that command (narrowed or removed since tracking). The check is **one-directional**: `policy_commands` running MORE than `declared_commands` named is not itself a finding — the spec's promise is a floor, not a ceiling.
- Both new finding codes classify at a tier the closed lattice (AD-31) cannot waive to `clean` — matching AD-49's own text ("an untraceable or mismatched binding cannot itself be waived to green"). Check `core/verdict.py`'s existing `_CLASSIFY_TABLE` tiers before picking one; reuse the same tier `--scope-check`'s own hard findings (`MRS-GATE-007`/`008`) already use rather than inventing a new severity story.
- Wired into `cli/gate.py::run_evaluate` (the Code Map's own `core/gate.py`/`core/spec_binding.py` listing is the pure core; some impure wiring is unavoidable to make this real, matching every prior story's own Spec Change Log precedent of the Surface field being approximate). Reuses the **existing** `--story`/`_find_spec_text` machinery Story 2.3 already added — no new CLI flag. Whenever `--story` is supplied (with or without `--scope-check`), the spec-binding check runs: `_find_spec_text` locates the tracked spec, `parse_success_signal` extracts its Commands, `check_spec_binding` compares against `effective.verify_commands`.

**Never:**
- No new CLI flag — reuse `--story`.
- No warning-tier finding for a binding mismatch — it must affect the verdict (AD-49, AD-31).
- Do not re-parse or duplicate `--scope-check`'s own spec-lookup (`_find_spec_text`) — one call per invocation, its result used for both checks when both are requested.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tracked spec, all declared commands still run | `declared_commands` ⊆ `policy_commands` | No finding | No error |
| Tracked spec, one declared command removed from policy | Declared command absent from `policy_commands` | One `Finding` naming the removed command; verdict cannot be `clean` | No error |
| Tracked spec, `## Verification` section missing | `parse_success_signal` returns `None` | One `Finding`: "no Success signal to bind against" | No error |
| No `--story` supplied | Story key unknown | Spec-binding check skipped entirely — cannot bind against an unknown story (matches `--scope-check`'s own existing precondition) | No error |
| `--story` supplied, no tracked spec exists for that key | `_find_spec_text` returns `None` | Same as "missing binding" — one `Finding` | No error |
| Policy runs a command the spec never declared | `policy_commands` ⊃ `declared_commands` | No finding — extra commands are not a contract breach | No error |
| Malformed `**Commands:**` bullet (no backtick-quoted command) | e.g. a bullet with prose only | That bullet is skipped, not a parse failure for the whole section | No error, degrades gracefully |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/spec_binding.py` — NEW. `parse_success_signal`.
- `src/pyforge/marshal/core/gate.py` — EDIT. `check_spec_binding`.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. Two new codes: missing-binding, narrowed/removed-command — both classified at the same non-waivable tier `--scope-check`'s own hard findings use.
- `src/pyforge/marshal/cli/gate.py` — EDIT. Wire the check into `run_evaluate` behind the existing `--story` flag, reusing `_find_spec_text`.
- `tests/unit/test_spec_binding.py` — NEW. `parse_success_signal` parsing matrix (present, absent, malformed bullet).
- `tests/unit/test_gate.py` — EDIT. `check_spec_binding` transition matrix, including the one-directional (extra-commands-ok) case.
- `tests/unit/test_cli.py` — EDIT. End-to-end `gate evaluate --story` binding tests.

## Tasks & Acceptance

**Execution:**
- [x] `core/spec_binding.py` — `parse_success_signal`, pure.
- [x] `core/gate.py` — `check_spec_binding`, pure, one-directional.
- [x] `core/findings.py` / `core/verdict.py` — register both codes at a non-waivable tier.
- [x] `cli/gate.py` — wire behind existing `--story`, reuse `_find_spec_text`.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation. (No scope narrowed; nothing logged -- see Spec Change Log below for the two additive edge-case decisions the matrix left open.)

**Acceptance Criteria:**
*(Story 2.7's ACs from `epics.md`, preserved as the contract of record.)*
- [x] Given a story with a tracked `specs/spec-<key>.md`, when its gate is evaluated, then the verify commands run are confirmed against the ones named in the spec's Success signal
- [x] And a narrowed or removed verify command since tracking is a registered finding, not a warning folded into an otherwise-green verdict
- [x] Given a story with no tracked spec to bind against, when its gate is evaluated, then the missing binding is reported explicitly as a finding, never evaluated silently against nothing
- [x] And an untraceable or mismatched binding cannot be waived to green — it participates in the closed admission lattice (AD-31) like every other criterion

## Design Notes

**Why the Success-signal parser targets `## Verification` → `**Commands:**` specifically, not a new frontmatter field.** Every spec authored this session already carries exactly this section in exactly this shape, unprompted — it predates this story by three stories (2.3, 3.7, 3.8) and needed no retrofitting. Inventing a second, redundant "success signal" field (e.g. in frontmatter) would create two sources of truth for the same fact; the existing Verification section already is the canonical Success signal, just previously unparsed.

**Why this depended on Story 4.1.** `_find_spec_text` (Story 2.3) reads from `planning-artifacts/specs/`, the TRACKED archive — until Story 4.1 shipped, that archive had no automated writer, so a story's spec could sit unpromoted indefinitely and this check would report "missing binding" for every story, including ones with a perfectly good spec sitting unpromoted in Tier-3. With 4.1 merged, the archive is a live, growing surface this check can actually bind against.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold (AD-4 core purity for `parse_success_signal`/`check_spec_binding`).

**Manual checks (if no CLI):**
- Run `marshal deploy promote` for real against this repo (Story 4.1, now merged) to populate `planning-artifacts/specs/` with this story's own siblings, then `marshal gate evaluate --story 2-7` against a worktree and confirm the binding check runs against a real tracked spec. (Not run as part of this implementation task -- `marshal deploy promote` makes a real git commit, and the decision to run it for real against this repo belongs to the human operator, matching Stories 2.3/4.1's own precedent of relying on the unit-test suite only.)

## Spec Change Log

**1. Two additive guard conditions, filling gaps the I/O & Edge-Case Matrix left open -- never contradicting a stated row.** The matrix names seven rows; two real states it does not enumerate needed a decision during wiring, both resolved by extending an existing precedent already in this same story rather than inventing a new one:

- **No resolvable active project.** The matrix's own "No `--story` supplied" row skips the check because "cannot bind against an unknown story"; it does not say what happens when `--story` resolves fine but the active project itself does not (`--project ""`, or an invalid slug). Symmetric reasoning applies: there is no `specs/` directory to look in without a resolved project, so the binding check is skipped the same way, mirroring `--scope-check`'s own existing `MRS-GATE-009` "no resolvable active project" precondition (same module, same story's Boundaries bullet: "Reuses the **existing** `--story`/`_find_spec_text` machinery Story 2.3 already added"). Verified live: without this guard, `test_gate_evaluate_scope_check_without_active_project_reports_mrs_gate_009` (Story 2.3, unmodified by this story) would regress from exit 1 (`unevaluable`) to exit 2 (`scope_violation`), since a resolved-but-unbindable story would otherwise report `MRS-GATE-010` (`SCOPE_VIOLATION`, the stronger rung) alongside the pre-existing `MRS-GATE-009` (`UNEVALUABLE`).
- **`--run <id>` requested but its fold unavailable.** `--scope-check`'s own existing behavior (`_run_scope_check`'s `run_requested and fold_result is None` branch, Story 2.3) omits its result entirely here, because `MRS-GATE-005` already reports the one root cause and a second finding would be a redundant symptom of it. The spec-binding check reuses the identical guard for the identical reason -- `MRS-GATE-005` is exactly as much the root cause of "the binding check could not run" as it is of "the scope check could not run". Verified live: `test_gate_evaluate_scope_check_run_scope_unavailable_omits_scope_check_data` (Story 2.3, unmodified) pins `codes == ["MRS-GATE-005"]` exactly; without this guard the new binding check would add `MRS-GATE-010` to that list and change the verdict.

Neither decision narrows a stated behavior or contradicts the Never clauses -- both are the same "cannot honestly evaluate this" reasoning the spec's own Boundaries bullet already established, applied to the two real gaps the matrix's seven rows did not name. No `deferred-work.md` entry: nothing was deferred or narrowed, only decided.

**2. Two pre-existing Story 2.3 tests (`test_gate_evaluate_scope_check_multiline_surface_block_reports_mrs_gate_009`, `test_gate_evaluate_scope_check_vcs_failure_reports_mrs_gate_009`) gained a tracked spec fixture with a bare `## Verification` section (no `**Commands:**`).** Both pin `exit_code == 1` for an UNEVALUABLE-tier `MRS-GATE-009` in isolation. Since the spec-binding check now runs unconditionally off `--story` (this story's own Boundaries bullet), and neither test's own scenario provided a tracked spec, `parse_success_signal` would otherwise return `None` and `check_spec_binding` would add `MRS-GATE-010` (`SCOPE_VIOLATION` -- a STRONGER rung than `UNEVALUABLE`), silently flipping both tests' exit code to 2. A `## Verification` heading with no `**Commands:**` sub-list parses to `()` (empty, not `None` -- this module's own None-vs-empty-tuple discipline), which `check_spec_binding` reports no finding for, restoring each test's original isolation. Verified live: both tests pass unmodified in assertions, only their fixtures gained the neutral section.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 1, medium 4, low 1)
- defer: 3
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **The spec-binding guard in `cli/gate.py::run_evaluate` silently dropped a project-resolution failure instead of reporting it.** The guard folded "the active project resolves" into a bare `and policy._is_valid_project_slug(project_slug)` alongside `story_key is not None`, so an empty or syntactically-malformed `--project`/active project produced NO finding and NO `spec_binding` key at all -- inconsistent with `--scope-check`'s own identical precondition, which loudly emits `MRS-GATE-009` ("no resolvable active project") for the exact same root cause. Fixed by splitting the guard: when the project does not resolve, the block now appends the SAME `MRS-GATE-009` finding `--scope-check` would emit, regardless of whether `--scope-check` was also requested. `test_gate_evaluate_story_no_resolvable_project_skips_binding_check` was replaced (it short-circuited on truthiness and never exercised `_is_valid_project_slug` at all) by `test_gate_evaluate_story_no_resolvable_project_reports_mrs_gate_009` (the empty-string case, now asserting the loud finding) and a new `test_gate_evaluate_story_syntactically_invalid_project_reports_mrs_gate_009` (a non-empty, syntactically-invalid slug -- the actual validity-check code path).
  - `[medium]` `[patch]` **`check_spec_binding` reported one `MRS-GATE-011` per repetition of a declared command, not per distinct command.** A spec whose `**Commands:**` list accidentally repeated the same missing command string produced N identical findings for one fact. Fixed: `declared_commands` is deduplicated (order-preserving, `dict.fromkeys`) before iterating. New test: `test_check_spec_binding_repeated_declared_command_reports_one_finding`.
  - `[medium]` `[patch]` **`data["spec_binding"]["violations"]` conflated "no spec tracked at all" with "exactly one command narrowed" -- both read `1`.** A downstream JSON consumer could not distinguish `declared_commands is None` from a genuine single `MRS-GATE-011`. Fixed: added `data["spec_binding"]["has_binding"]` (`True` when `declared_commands is not None`, `False` otherwise), `violations` left unchanged as a total count. New assertions in `test_gate_evaluate_story_with_no_tracked_spec_reports_mrs_gate_010` (`has_binding is False`) and `test_gate_evaluate_story_declared_commands_subset_of_policy_no_binding_finding` (`has_binding is True`).
  - `[medium]` `[patch]` **`core/spec_binding.py`'s heading regexes anchor on `re.MULTILINE`'s `$`, which does not match before a trailing `\r`, so a CRLF-terminated spec file would fail to match `## Verification` at all** and silently fall through to `None` ("nothing to bind against") even though the section is genuinely present. Fixed: `parse_success_signal` normalizes `\r\n`/`\r` to `\n` up front, before any regex work, rather than making every regex CRLF-aware. New test: `test_parse_success_signal_crlf_terminated_spec_still_parses`.
  - `[medium]` `[patch]` **`check_spec_binding` compared commands via exact-string membership with no whitespace normalization**, so a spec bullet and a policy entry differing only by incidental whitespace (e.g. a double space) would false-positive as narrowed/removed. Fixed: both sides are compared after collapsing whitespace runs to a single space (`" ".join(command.split())`) -- deliberately shallow, no shell-argument-aware parsing. New test: `test_check_spec_binding_incidental_whitespace_difference_is_not_a_finding`.
  - `[low]` `[patch]` **`test_parse_success_signal_em_dash_variant_also_parses` claimed to test em-dash handling but exercised nothing dash-specific** (`_BULLET_COMMAND` has no dash-specific logic -- it only ever captures text between the two backticks). Renamed to `test_parse_success_signal_trailing_prose_after_closing_backtick_is_ignored` with a corrected comment describing what it actually verifies.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` `cli/gate.py::run_evaluate` reaches into `core/policy.py`'s private `_is_valid_project_slug` helper across a module boundary, and calls it twice per invocation (once for `spec_text`, again in the spec-binding guard) -- an encapsulation smell and redundant computation this same guard's own surrounding "resolved exactly once" framing otherwise avoids. Fixing it needs either a public accessor or threading a single computed result through both call sites, bigger than the P1 patch above (which deliberately preserves the existing duplication).
  - `[medium]` The `_render_text` spec-binding summary line reports only a story key and a bare violation count, never which command(s) were narrowed -- that detail exists only in the separately-rendered `findings:` block. A comment claiming this text projection "carries the same data as --format json" overstates it (the JSON's `declared_commands` field has no text-format analogue). Cosmetic; out of this pass's scope.
  - `[medium]` `check_spec_binding` only compares against the static `effective.verify_commands` value -- it has no way to detect whether a declared command is actually REACHABLE/exercised for the current gate mode or run scope (e.g. a `--run`-scoped evaluation runs no commands at all, yet the binding check still runs against the seed's `verify_commands`). Needs a real design decision on what "reachable" means here, not a mechanical patch.

</intent-contract>

## Suggested Review Order

**Pure core**

- Entry point: the Success-signal parser — read this first to see the exact markdown shape it targets (verified live against 2.3/4.1's own promoted specs), including the P4 CRLF-normalization fix.
  [`spec_binding.py:68`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_binding.py#L68)

- `check_spec_binding`: one-directional comparison, the P2 dedup fix, and the P6 whitespace-normalization fix.
  [`gate.py:426`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py#L426)

**CLI wiring — the P1 fix**

- `run_evaluate`'s spec-binding block: now emits `MRS-GATE-009` on a non-resolving project (was a silent skip before review), and the P3 `has_binding` payload field.
  [`gate.py:629`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py#L629)

**Tests (peripherals)**

- Parsing matrix, including the P4/P5 CRLF and renamed-test fixes.
  [`test_spec_binding.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_spec_binding.py#L1)

- `check_spec_binding` transition matrix.
  [`test_gate.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_gate.py#L1)

- End-to-end CLI tests, including the P1 non-resolving-project regression test.
  [`test_cli.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_cli.py#L1)
