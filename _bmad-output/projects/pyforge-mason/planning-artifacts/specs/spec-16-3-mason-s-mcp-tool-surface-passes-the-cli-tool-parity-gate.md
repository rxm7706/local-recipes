---
title: "Mason's MCP tool surface passes the CLI-tool parity gate"
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '57c001c9d7c8864ec235b871c8e3dc024845e414'
review_loop_iteration: 2
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      No CI path exercises `.claude/skills/conda-forge-expert/tests/meta/test_mcp_cli_tool_parity.py`
      when marshal's `pyforge.marshal.mcp.parity` public surface changes on the marshal side only.
    evidence: |-
      `cfe-regression-net.yml` (the only workflow that runs this test) has no
      `src/shared/packages/pyforge-marshal/**` path trigger; `pyforge-station-tests.yml` triggers on
      that path but only runs marshal's own test suite, never the CFE skill's tests. A marshal-only
      commit that changes `ParityFinding`'s fields or `assert_cli_tool_parity`/`parity_findings`'s
      signatures (updating marshal's own call sites and `TOOL_SPECS` to match, so marshal's own suite
      stays green) would ship green with `mcp_cli_parity.py`'s now-mismatched call into that API never
      exercised. Verified via review pass 3's Verification Gap layer reading both workflow files'
      `paths:` filters directly.
    location: >-
      .github/workflows/cfe-regression-net.yml
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Parity between a station's CLI verbs and its MCP tools is a gated number, not review
— but only for marshal. `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py`
drives `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`,
`parity_findings`, `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES`
allowlists) against live `TOOL_SPECS`. Mason's own 46 `@mcp.tool` registrations in
`.claude/tools/conda_forge_server.py` have **no parity gate at all** — a CLI wrapper can gain or
lose a verb with no tool counterpart and nothing reds. This is one of the fleet-readiness pass's
coverage gaps (2026-09-09, C6).

**Approach:** Extend marshal's existing primitive over the CFE server rather than re-implementing
it — derive the CLI surface from `.claude/scripts/conda-forge-expert/` and the pixi task registry,
derive the tool surface from the live `@mcp.tool` registrations, and declare every deliberate
asymmetry in an explicit allowlist carrying a one-line reason (not a silent skip). Add a new
parity meta-test under `.claude/skills/conda-forge-expert/tests/meta/` proving the gate both
passes clean today and can actually fail (fixture-injected mismatches in each direction).

## Boundaries & Constraints

**Always:**
- Extend marshal's `pyforge.marshal.mcp.parity` primitive over the CFE server; do not
  re-implement or fork a second independent copy of the gate — the CFE skill records explicitly
  that a second independent copy of a gate is how the `_http.py` credential leak survived a
  "durable fix."
- Every deliberate CLI-only or tool-only asymmetry must be declared in an explicit allowlist with
  a one-line reason, never a silent skip.
- Add a fixture-injected mismatch test in **each** direction — an on-surface CLI verb with no
  tool counterpart, and a tool with no CLI verb and no allowlist entry — and prove the gate
  actually **fails** on each, not merely that it passes today.
- If a shared helper is needed rather than a mason-local copy, propose it to marshal.
- If a new script is added as part of this work, follow the repo's three-place rule (canonical
  implementation, CLI wrapper, pixi task + `SCRIPTS` list entry in
  `test_all_scripts_runnable.py`).
- This is CFE-surface + tool-surface work — runs through `conda-forge-expert` (Rule 1) and ends
  with the Rule-2 retro.

**Never:**
- Do not touch `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` — atlas's half
  of the marshal C10 routing is atlas's story to mint, not mason's.
- Do not fork `pyforge.marshal.mcp.parity` into a mason-local independent copy.
- Do not silently skip an asymmetry — every CLI-only/tool-only case needs a declared, reasoned
  allowlist entry.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live inventory, no fixtures | Real CLI surface (`.claude/scripts/conda-forge-expert/` + pixi tasks) vs. real 46 `@mcp.tool` registrations | Parity gate passes clean; every real asymmetry is in the declared allowlist | N/A |
| Fixture-injected CLI-only mismatch | A synthetic on-surface CLI verb with no tool counterpart and no allowlist entry | Parity gate **fails**, proving the gate can detect this direction | Test asserts the failure occurs, not just that the gate ran |
| Fixture-injected tool-only mismatch | A synthetic tool with no CLI verb and no allowlist entry | Parity gate **fails**, proving the gate can detect this direction | Test asserts the failure occurs, not just that the gate ran |
| Deliberate asymmetry | A real CLI-only or tool-only case exists by design | Present in an explicit allowlist with a one-line reason | Missing/undocumented allowlist entry is itself a finding |
| Atlas boundary | Story execution reaches for `pyforge.atlas.mcp.tools` | Out of scope — this story touches no atlas file | N/A |

</intent-contract>

## Code Map

- `.claude/tools/conda_forge_server.py` — the 46 `@mcp.tool` registrations that become this
  story's tool-surface source; a declared CLI↔tool mapping (or allowlist) may be added here or
  alongside it.
- `.claude/skills/conda-forge-expert/tests/meta/` (new file) — the new parity meta-test, mirroring
  `pyforge-marshal/tests/meta/test_cli_tool_parity.py`'s shape (live-inventory pass + two
  fixture-injected failure cases).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py` (read-only / extension
  point) — `assert_cli_tool_parity`, `discover_cli_verbs`, `parity_findings`, `tools_by_cli_verb`;
  the primitive this story extends over the CFE server rather than re-implementing.
- `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` (read-only reference) —
  the existing marshal-only gate this story generalizes the pattern from.
- `.claude/scripts/conda-forge-expert/` **and** `pixi.toml`'s **full task registry** — **both** are
  required CLI-surface sources, not the wrapper directory alone: many pixi task names diverge from
  their underlying wrapper file's stem (task `check-deps` → wrapper `dependency-checker.py`; task
  `recipe-build` → wrapper `native-build.sh`; task `recipe-build-cross` → wrapper `cross-build.sh`;
  tasks `build-local`/`build-local-all`/`build-local-check`/`build-local-setup-sdk` all → wrapper
  `local_builder.py`). Anchor the gate's notion of "CLI verb" at the **pixi task name** — the actual
  `pixi run -e <env> <verb>` surface a person or agent invokes — not the wrapper file's stem; a
  wrapper-stem-only derivation cannot detect a pixi task being renamed, added, or removed independent
  of its file, which is exactly the drift class this story exists to close (2026-09-10 amendment).
  **Scan every `[feature.*.tasks.*]` table, not `local-recipes` alone** — `[feature.vuln-db.tasks.*]`
  also invokes `.claude/scripts/conda-forge-expert/` wrappers (`scan-project` → `scan_project.py`,
  the same script the `scan_project` MCP tool references; `detail-cf-atlas-vdb` and
  `inventory-channel` are two more), and scoping to one feature silently misses real matches in
  another — exactly the gap a second review pass caught (2026-09-10 amendment #2 — see Spec Change
  Log). Reconcile the `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES` allowlists and the parity meta-test's
  fixtures to the full-registry, task-name vocabulary accordingly.
- `pixi.toml` — also a new task if the parity check needs its own pixi entry point (mirroring how
  other detectors/checks are wired).
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — `SCRIPTS` list
  gains an entry if a new canonical script is added (three-place rule).

## Tasks & Acceptance

**Execution:**
- `[feature]` Extend `pyforge.marshal.mcp.parity` (or a shared helper proposed to marshal) to
  derive the CFE server's CLI surface (`.claude/scripts/conda-forge-expert/` + pixi task registry)
  and its tool surface (live `@mcp.tool` registrations in `conda_forge_server.py`).
- `[feature]` Declare every real, deliberate CLI-only/tool-only asymmetry in an explicit allowlist
  with a one-line reason each.
- `[feature]` Add the new parity meta-test under `.claude/skills/conda-forge-expert/tests/meta/`:
  a live-inventory clean-pass case, plus one fixture-injected CLI-only-mismatch failure case and
  one fixture-injected tool-only-mismatch failure case.
- `[chore]` If a new canonical script is added, wire the three-place rule (canonical
  implementation + CLI wrapper + pixi task and `SCRIPTS` list entry).

**Acceptance Criteria:**
- Given parity between a station's CLI verbs and its MCP tools is a gated number, not review, for
  marshal only — `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` drives
  `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`, `parity_findings`,
  `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES` allowlists) against live
  `TOOL_SPECS` — while mason's 46 `@mcp.tool` registrations in `.claude/tools/conda_forge_server.py`
  have no parity gate at all, so a CLI wrapper can gain or lose a verb with no tool counterpart
  and nothing reds.
- When marshal's primitive is extended over the CFE server rather than re-implemented — the CLI
  surface derived from `.claude/scripts/conda-forge-expert/` and the pixi task registry, the tool
  surface from the live `@mcp.tool` registrations, with every deliberate asymmetry declared in an
  explicit allowlist carrying a one-line reason (not a silent skip).
- Then the live inventory passes clean, a fixture-injected mismatch in each direction (an
  on-surface CLI verb with no tool; a tool with no CLI verb and no allowlist entry) fails the gate
  — proving the gate can fail, not merely that it passes — and the parity number is reported
  rather than asserted by review.
- Boundary: atlas's half of the marshal C10 routing (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py`)
  is atlas's story to mint, not mason's; this story touches no atlas file. If the extension needs
  a shared helper rather than a mason-local copy, propose it to marshal rather than forking
  `pyforge.marshal.mcp.parity` — a second independent copy of a gate is how the `_http.py`
  credential leak survived a "durable fix," and the CFE skill records that lesson explicitly.
  Rule 1 applies throughout; the effort ends with the Rule-2 retro.

## Spec Change Log

### 2026-09-10 — bad_spec amendment (triggered by review pass 1, finding EC7/IA-primary)

**Triggering finding:** the Code Map's own guidance (previously: "`.claude/scripts/conda-forge-expert/`
— the CLI-surface source ... this story's derivation reads from") named only the wrapper directory,
dropping the Approach/Acceptance-Criteria's explicit "and the pixi task registry" half. The
implementation followed the narrower, more concrete Code Map bullet over the less-directive Approach
prose, and keyed its notion of "CLI verb" on internal wrapper-file stems (`native-build`, `cross-build`,
`local_builder`, `dependency-checker`) rather than the pixi task names a person or agent actually
invokes (`recipe-build`, `recipe-build-cross`, `build-local`/`build-local-all`/`build-local-check`/
`build-local-setup-sdk`, `check-deps`).

**Known-bad state avoided:** shipping a "CLI↔tool parity gate" that is silently blind to a pixi task
being renamed, added, or removed independent of its underlying wrapper file — exactly the drift class
this story exists to close.

**What was amended:** the Code Map bullet for the CLI-surface source, below — now explicitly requires
both sources and names the concrete stem/task-name divergences found during review, so re-derivation
anchors "CLI verb" at the pixi task name.

**KEEP instructions for re-derivation (verified working in the reverted attempt, must survive):**
- Extend marshal's `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`/`parity_findings`) unmodified
  via a `sys.path` insert — never fork it.
- The `CLI_ONLY_VERBS` / `TOOL_ONLY_NAMES` two-allowlist shape, each entry carrying a one-line reason.
- Fixture-injected failure tests proving **both** directions actually fail (an on-surface CLI verb with
  no tool; a tool with no CLI verb and no allowlist entry), asserting the failure occurs, not just that
  the gate ran.
- A hand-override mechanism for the one case static analysis can't disambiguate on its own
  (`prepare_submission_branch` claims `prepare_pr`, not `submit_pr`, even though both wrapper files
  delegate to the identical canonical `submit_pr.py` script).
- The Rule-1/Rule-2 commit-separation convention: a plain `feat(mason):` commit for the mason-owned
  derivation code, and a separate sanctioned `retro(cfe):` commit (moving `CHANGELOG.md`) for the
  CFE-skill-surface touch.
- No atlas file touched; no fork of the marshal primitive.

### 2026-09-10 — bad_spec amendment #2 (triggered by review pass 2, Intent Alignment primary divergence)

**Triggering finding:** the first amendment's own Code Map wording narrowed "the pixi task registry"
to `pixi.toml`'s `[feature.local-recipes.tasks.*]` table specifically — that scoping was mine, not
sourced from the intent-contract, which says "the pixi task registry" unqualified. `[feature.vuln-db
.tasks.*]` also invokes `.claude/scripts/conda-forge-expert/` wrappers: `scan-project` runs the
identical `scan_project.py` the `scan_project` MCP tool references, and `detail-cf-atlas-vdb` /
`inventory-channel` are two more CFE-wrapper tasks invisible to the gate under the local-recipes-only
scope. `scan_project` is currently misfiled in `TOOL_ONLY_NAMES` as a deliberate asymmetry it is not.

**Known-bad state avoided:** shipping a gate that still silently misses a real CLI↔tool
correspondence — this time at the pixi-*feature* boundary rather than the wrapper-stem boundary pass
1 fixed — and that documents a non-asymmetry as a declared, reasoned allowlist entry, undermining the
allowlist's own credibility as an exhaustive list of *real* asymmetries.

**What was amended:** the Code Map bullet below now requires scanning every pixi feature's task table
(not just `local-recipes`) for `.claude/scripts/conda-forge-expert/`-invoking commands, worded
generally so a future new feature is covered without another amendment.

**KEEP instructions for re-derivation (verified working in the reverted attempt, must survive, in
addition to amendment #1's KEEP list above):**
- Anchor CLI verbs at the pixi task name, not the wrapper file stem (amendment #1's fix — this part
  was correct and must not regress).
- The `tomllib`-based `pixi.toml` parsing approach and the `cmd`-regex-match-on-`.claude/scripts/
  conda-forge-expert/` detection.
- The `_VERB_OVERRIDE` hand-override mechanism and pattern.
- Re-verify: once `vuln-db` tasks are in scope, `scan_project` should auto-resolve to `scan-project`
  and leave `TOOL_ONLY_NAMES`; `detail-cf-atlas-vdb` and `inventory-channel` need a `CLI_ONLY_VERBS`
  entry (or auto-resolve, if a tool turns out to claim them) with a one-line reason each; the existing
  `detail-cf-atlas`/`build-cf-atlas`/`atlas-phase` task names are already defined once per feature
  under the same name, so widening scope does not duplicate or rename them.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 19 findings — high 0, medium 2, low 14, false 3, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: `reference/mcp-tools.md`'s new bullet says "this file's 46 `@mcp.tool()` registrations", but "this file" is `mcp-tools.md` itself (already used self-referentially on its own line 3), not `conda_forge_server.py` — the sentence's referent is backwards. Action: reworded to name `conda_forge_server.py` explicitly.
  - `[low]` `[reject]` Blind Hunter: `_script_stem_constants()` matches any `NAME = X <binop> "*.py"`-shaped assignment without checking the operator is division or the left operand is `SCRIPTS_DIR`, looser than its own docstring claims. No live false positive today (the live gate passes clean); fix requires adding a new guard for a case that does not occur in the current file — unlikely in everyday use and the fix is more than a direct correction.
  - `[low]` `[reject]` Blind Hunter: `build_tool_specs()`'s verb detection walks the whole tool-function body for any reference to a known script constant rather than restricting to a `_run_script(...)` call argument, contrary to its own docstring. Verification-gap layer independently confirmed all 37 claiming tools map 1:1 cleanly today; fix requires restructuring the AST walk for a case that does not occur live.
  - `[low]` `[reject]` Blind Hunter: when a tool body legitimately references 2+ script-path constants that both resolve to live verbs, `build_tool_specs()` silently takes `sorted(...)[0]` with no signal of ambiguity, and no test exercises this. Verification-gap layer confirmed no live tool triggers this; fix requires a new guard/branch for a hypothetical case.
  - `[low]` `[patch]` Blind Hunter: both `except ImportError` blocks in `test_mcp_cli_tool_parity.py` assign to `_import_error` but it is never read in the `skipif` reason, so a genuine bug in `pyforge.marshal.mcp.parity` would misreport as "monorepo not checked out." Plausible during future marshal maintenance and the fix is a direct one-line interpolation — not rejected. Action: patched.
  - `[low]` `[reject]` Blind Hunter: `discover_cli_verbs()`/`discover_tool_names()` have no existence guard on `_CLI_WRAPPER_DIR`/`_TOOLS_FILE`; a partial checkout would crash instead of skip cleanly. The trigger requires marshal's src present but the CFE tools/scripts dir absent within the same repo — an inconsistent, unlikely state; fix requires new guards for this narrow case.
  - `[low]` `[patch]` Blind Hunter: `TOOL_ONLY_NAMES["migrate_to_v1"]`'s reason introduces a third name "migrate" not used as a tracked verb/tool anywhere else, confusing a future reader. Fix is a direct reword. Action: patched.
  - `[false]` `[reject]` Blind Hunter: implies `mcp_cli_parity.py` should get a CLI wrapper/pixi task/`SCRIPTS`-list entry under the three-place rule. Disproven: `conda_forge_server.py`, the MCP-server file living in the same `.claude/tools/` directory, has never had a CLI wrapper, pixi task, or `SCRIPTS`-list entry either (verified: no match in `pixi.toml` or `test_all_scripts_runnable.py`'s `SCRIPTS` list); the three-place rule targets `.claude/skills/conda-forge-expert/scripts/` CI scripts, not `.claude/tools/` library modules.
  - `[low]` `[defer]` Blind Hunter: the CHANGELOG's "TL;DR — what's new in the latest release" section keeps accumulating full paragraphs (now 3) instead of trimming to the newest. Pre-existing pattern — the section already held 2 full paragraphs (v8.90.2 + v8.90.1) before this diff; this commit only continues the established convention, not introduced by this story.
  - `[low]` `[reject]` Edge Case Hunter: no existence guard on `_CLI_WRAPPER_DIR` (same root cause as the Blind Hunter existence-guard finding above) — merged, same verdict/route.
  - `[low]` `[reject]` Edge Case Hunter: `_script_stem_constants()` matches any binop/operand shape ending in `.py`/`.sh` (same root cause as the Blind Hunter constant-detection finding above) — merged, same verdict/route.
  - `[low]` `[reject]` Edge Case Hunter: verb detection walks the whole tool body, not just `_run_script(...)` call args (same root cause as the Blind Hunter verb-attribution finding above) — merged, same verdict/route.
  - `[low]` `[reject]` Edge Case Hunter: multi-reference ambiguity silently resolved alphabetically (same root cause as the Blind Hunter tie-break finding above) — merged, same verdict/route.
  - `[low]` `[reject]` Edge Case Hunter: `_is_mcp_tool` only matches `@mcp.tool()` call form, not a bare `@mcp.tool` attribute decorator; such a tool would silently vanish from the whole inventory. Confirmed via `grep`: every one of the file's 20+ `@mcp.tool` decorators uses call form today, zero bare-attribute uses; fix requires a new branch for a form not used anywhere in this codebase.
  - `[low]` `[reject]` Edge Case Hunter: a future `@mcp.tool(name="...")` override isn't read, so the inventory key could diverge from the registered tool name. Confirmed via `grep`: zero `name=` overrides exist today; fix requires new kwarg-reading logic for a form not used anywhere.
  - `[medium]` `[bad_spec]` Edge Case Hunter (claim, pre-verified): the CLI surface is derived only from `.claude/scripts/conda-forge-expert/` wrapper-file stems; `pixi.toml` is never parsed, despite the spec's Approach/Acceptance-Criteria/I-O-Matrix all naming "the pixi task registry" as a required second source. Verified directly: `dependency-checker.py`'s real pixi task is `check-deps`; `native-build.sh`/`cross-build.sh` bind to tasks `recipe-build`/`recipe-build-cross`; `local_builder.py` binds to four distinct tasks (`build-local`, `build-local-all`, `build-local-check`, `build-local-setup-sdk`) — none of these real, user-facing pixi verbs ever appear in `discover_cli_verbs()`'s output or the allowlists, which key on internal file stems instead. A pixi task renamed, removed, or added independent of its wrapper file would pass the gate silently. Action: Code Map amended (see Spec Change Log); code reverted and re-derived.
  - `[medium]` `[bad_spec]` Intent Alignment Auditor (primary divergence): same root cause and evidence as the Edge Case Hunter pixi-registry finding above — merged, same verdict/route.
  - `[false]` `[reject]` Intent Alignment Auditor (secondary divergence): claims Rule 2's retro-closure isn't evidenced because the CHANGELOG entry reads as a shipped-feature description rather than a Corrections/Refinements/Additions-framed retro, unlike the adjacent v8.90.2 entry's tracked `DW-*` deferral. Disproven: commit `31d8059330` carries the sanctioned `retro(cfe):` subject and moves `CHANGELOG.md` (verified via `git show --stat`), satisfying `test_persona_consults_cfe.py`'s `unsanctioned_commits` guard exactly; every other CFE CHANGELOG entry in this same diff (v8.90.2, v8.90.1, v8.90.0) is written in the identical prose-narrative shape with no literal Corrections/Refinements/Additions headings, so this entry matches the repo's actual, working convention. The `DW-*` tracked-deferral shape applies only when a retro finding is deferred to a later story, not when it lands immediately as here.
  - `[false]` `[reject]` Intent Alignment Auditor (tertiary divergence): same root cause and evidence as the Blind Hunter three-place-rule finding above — merged, same verdict/route.

### 2026-09-10 — Review pass 2

- verdicts: 21 findings — high 0, medium 1, low 16, false 4, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: `test_discover_covers_all_46_tools` hardcodes `== 46` with no comment telling a future contributor the number must move when a tool is added/removed. Direct fix: add that comment.
  - `[low]` `[patch]` Blind Hunter: no test pins the specific fix this story exists to make (verbs anchored at the pixi **task name**, not the wrapper stem) — coverage relies only on "live inventory passes clean," which would not necessarily catch a silent regression back to stem-anchoring if allowlists were adjusted to compensate. Direct fix: add a small regression test asserting concrete task names (e.g. `check-deps`, `build-local`) are in `discover_cli_verbs()` and their old stems (`dependency-checker`, `local_builder`) are not.
  - `[low]` `[patch]` Blind Hunter: `_VERB_OVERRIDE["prepare_submission_branch"]` has no direct unit test asserting the resolved verb; only exercised indirectly via the full live-inventory pass. Direct fix: add a small assertion.
  - `[low]` `[patch]` Blind Hunter: the CHANGELOG v8.91.0 entry's and SKILL.md's "Files:" list omits `tests/meta/test_skill_md_consistency.py`, even though this same diff modifies that file in the identical `retro(cfe):` commit. Direct fix: add it to both lists.
  - `[false]` `[reject]` Blind Hunter: claims `TOOL_ONLY_NAMES["trigger_build"]`'s comment naming "recipe-build/-cross/-docker" as equivalents is inconsistent with `CLI_ONLY_VERBS` only listing two of the three. Disproven: verified `[feature.local-recipes.tasks.recipe-build-docker]`'s `cmd` is `python build-locally.py` at the repo root — it never matches the `.claude/scripts/conda-forge-expert/` wrapper regex at all, so it was never eligible to appear in `discover_cli_verbs()`'s output in the first place and needs no allowlist entry; the comment is accurate context, not a claimed allowlist obligation.
  - `[low]` `[defer]` `carried` Blind Hunter: the CHANGELOG's "TL;DR" section still accumulates full un-trimmed paragraphs (now 3) instead of summarizing only the newest release — same pre-existing pattern logged `[low][defer]` in review pass 1, still unaddressed, still not introduced by this diff.
  - `[false]` `[reject]` Blind Hunter: claims `followup_review_recommended: false` (set by the implementation subagent mid-run) is premature since the re-derived core logic hasn't been reviewed yet. Disproven: this field is recomputed fresh at every pass's `## Finalize` step from that pass's own triage outcome (workflow step-04 §Finalize), superseding whatever interim value the implementation subagent wrote; the re-derived logic *is* being reviewed in this very pass.
  - `[low]` `[reject]` Blind Hunter: claims a bare `ImportError` anywhere in `pyforge.marshal.mcp.parity`'s import chain (not just "monorepo not checked out") would silently skip the whole gate rather than fail it, violating "never a false green." Real, but the fix (distinguish "not checked out" from "genuinely broken" import failures) requires new conditional logic, not a direct correction, for a scenario a broken marshal-side change would already surface in marshal's own test suite first — unlikely in everyday use and the fix is more than a direct correction.
  - `[false]` `[reject]` Blind Hunter: claims the Review Triage Log's "37 claiming tools" (pass 1) doesn't arithmetically reconcile with this diff's "46 tools / 10 tool-only" (pass 2, implying 36). Disproven: the two figures describe two different code versions' derivations — pass 1's now-reverted wrapper-stem-based scheme claimed 37, pass 2's task-name-based scheme claims 36; both are internally correct for their own pass, not a live inconsistency.
  - `[low]` `[reject]` `carried` Blind Hunter / Verification Gap / Edge Case Hunter (three-way, same root cause): `_local_recipes_tasks()` only extracts `cmd` when `isinstance(cmd, str)`; a TOML array-valued `cmd` would be silently dropped from `discover_cli_verbs()`. Confirmed via direct scan: none of the 156 `local-recipes` tasks use array-form `cmd` today — unlikely in everyday use and the fix adds a new branch.
  - `[low]` `[reject]` Edge Case Hunter: a `local-recipes` task invoking 2+ CFE wrapper scripts in one `cmd` would only have the first attributed (`.search()`, not `.finditer()`). Confirmed via direct scan: no live task does this today — unlikely and the fix adds complexity.
  - `[low]` `[reject]` `carried` Edge Case Hunter: `_is_mcp_tool` only matches `@mcp.tool()` call form, not a bare `@mcp.tool` attribute decorator — same claim and code shape as review pass 1's rejected finding.
  - `[low]` `[patch]` Edge Case Hunter: `_is_mcp_tool`'s rewritten form dropped the `dec.func.value` / `.id == "mcp"` check pass 1's version had, so a call-form `.tool()` decorator on an unrelated object would now be misclassified as an MCP tool registration — a genuine regression against pass 1's own (already-adequate) code, not merely a hypothetical gap. No live effect today (no such decorator exists), but the fix is a direct one-line restoration of a check that already existed and was dropped, not new speculative complexity.
  - `[low]` `[reject]` `carried` Edge Case Hunter: no existence guard on `_TOOLS_FILE` — same claim and code shape as review pass 1's rejected finding (there, `_CLI_WRAPPER_DIR`/`_TOOLS_FILE`; the `_TOOLS_FILE` half recurs unchanged).
  - `[low]` `[reject]` Edge Case Hunter: no existence guard on `_PIXI_TOML`, and `_local_recipes_tasks()` indexes `data["feature"]["local-recipes"]["tasks"]` without `.get()` fallbacks — a missing/malformed `pixi.toml` would crash rather than skip cleanly. New location (pixi.toml parsing didn't exist in pass 1), but the trigger (the repo's own root manifest missing or restructured) would already break the entire build, not a realistic partial-checkout case — unlikely and the fix adds guards.
  - `[low]` `[reject]` `carried` Edge Case Hunter: ambiguous multi-constant tool references silently resolve via `sorted(...)[0]` — same claim and code shape as review pass 1's rejected finding.
  - `[low]` `[reject]` `carried` Edge Case Hunter: a future `@mcp.tool(name="...")` override isn't read — same claim and code shape as review pass 1's rejected finding.
  - `[medium]` `[bad_spec]` Intent Alignment Auditor (primary divergence): the CLI-verb derivation reads only `[feature.local-recipes.tasks.*]`, per the 2026-09-10 Code Map amendment itself — but the Approach/Acceptance-Criteria/I-O-Matrix say "the pixi task registry" unqualified, and `[feature.vuln-db.tasks.*]` also invokes `.claude/scripts/conda-forge-expert/` wrappers. Verified directly: `vuln-db.scan-project` runs `scan_project.py`, the identical script the `scan_project` MCP tool references — under the current local-recipes-only scope this real, resolvable match is instead misfiled in `TOOL_ONLY_NAMES` as a "deliberate asymmetry" it is not. Two more vuln-db-only CFE-wrapper tasks (`detail-cf-atlas-vdb`, `inventory-channel`) are invisible to the gate entirely. This reproduces the exact class of gap review pass 1 caught, one level up (pixi-feature scope instead of wrapper-stem naming). Action: Code Map amended again (see Spec Change Log); code reverted and re-derived.
  - `[false]` `[reject]` `carried` Intent Alignment Auditor (secondary divergence): re-raises the three-place-rule scope claim — same claim and code shape as review pass 1's rejected finding (disproof unchanged: `conda_forge_server.py` precedent).

### 2026-09-10 — Review pass 3

No `intent_gap`/`bad_spec` this pass — the Intent Alignment Auditor confirmed both prior scope gaps (wrapper-stem anchoring; local-recipes-only scanning) are closed: "the two gaps passes 1 and 2 left open... are both closed in this pass." Findings below are `patch`/`defer`/`reject` only, processed normally.

- verdicts: 18 findings — high 0, medium 6, low 9, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter (4 grouped rows — same root cause): the CHANGELOG's TL;DR section carries **two separate `v8.91.0` paragraphs** describing the same release with different text; the shorter one is tagged "current" and ends with a meaningless self-referential "See CHANGELOG."; the fuller, accurate paragraph (the one reflecting the actual review-pass fixes) is not marked current; and SKILL.md's Version History entry is a third, independently-worded paraphrase matching neither. Confirmed via direct `grep` — two `**v8.91.0**` lines exist in the TL;DR with materially different text. Action: patched — the stub paragraph deleted, the fuller paragraph is now the sole `v8.91.0` TL;DR entry marked `(current)`, and SKILL.md's Version History entry reworded to track it closely. Verified: `grep -c "^\*\*v8.91.0"` now returns 1; no "See CHANGELOG." stray sentence remains.
  - `[low]` `[reject]` Blind Hunter: `_cfe_pixi_tasks()` only scans `[feature.*.tasks.*]`, never a top-level `[tasks]` table shared across environments. Confirmed via direct parse: `pixi.toml` has no top-level `tasks` key today — the scenario cannot currently occur; unlikely and the fix adds a guard for a structure that doesn't exist.
  - `[low]` `[patch]` Blind Hunter: `ParityFinding` is imported from `pyforge.marshal.mcp.parity` but never referenced anywhere else in the module — confirmed via `grep`, a dead import. Action: patched — removed from both the live import and the `except ImportError` stub-assignment; confirmed 0 remaining references.
  - `[false]` `[reject]` Blind Hunter: claims the pass-2 Review Triage Log naming `test_discover_covers_all_46_tools` doesn't match this pass's `test_build_tool_specs_covers_all_46_tools`. Disproven: the pass-2 log entry is a dated historical record of pass-2's own (reverted) code; comparing it to pass-3's differently-shaped code is not a live inconsistency, the same pattern as pass-2's own disproven "37 vs 36" finding.
  - `[low]` `[reject]` Blind Hunter: the new `reference/mcp-tools.md` bullet sits among cf_atlas/JFrog/CVE-database operational notes rather than its own heading. Subjective placement preference with no functional consequence; unlikely to meaningfully confuse a reader and "the right place" is a judgment call, not a direct correction.
  - `[low]` `[patch]` Blind Hunter: the module docstring and CHANGELOG both promise "a missing **or stale** entry is itself a gate finding," but the two fixture tests only exercise the missing/undeclared direction (`cli_missing_tool`, `tool_without_cli`) — marshal's engine also emits `tool_only_has_cli`/`cli_only_has_tool` for a genuinely stale allowlist entry (confirmed by reading `parity.py`'s finding-code sites), and nothing here fixture-tests that direction. The live test already guards against a real stale entry existing today, but the story's own "prove the gate can fail" bar isn't fully met for this codepath. Action: patched — added `test_fixture_stale_cli_only_allowlist_entry_fails`, injecting a `CLI_ONLY_VERBS` entry (`"validate"`) a real tool actually claims and asserting `cli_only_has_tool` fires via `parity_findings()` plus that `assert_cli_tool_parity()` raises; verified passing (9/9 in the test file).
  - `[low]` `[reject]` Blind Hunter: four `TOOL_ONLY_NAMES` reasons cite `test_skill_md_consistency.py`'s `no_task_allowlist` with no live cross-check that those scripts are still listed there. Real but narrow; the fix (a cross-file consistency check) is meaningfully more than a direct correction for a documentation-currency risk, not a functional one.
  - `[low]` `[reject]` Edge Case Hunter: a task name shared across two pixi features could in principle map to two different scripts, silently misattributed. Confirmed via direct check: the three task names actually shared today (`atlas-phase`, `build-cf-atlas`, `detail-cf-atlas`) all resolve to the identical wrapper stem in both features (the regex ignores CLI flags, so `detail_cf_atlas.py` vs `detail_cf_atlas.py --vdb` still yield the same stem) — no live conflict exists; unlikely and the fix adds a guard for a case with zero current instances.
  - `[low]` `[reject]` Edge Case Hunter: a pixi task expressed in short (bare-string) form rather than a table would crash `_cfe_pixi_tasks()` on `task.get("cmd")`. Confirmed via direct scan of all features: zero short-form task entries exist in `pixi.toml` today; unlikely and the fix adds a guard for a form not used anywhere in this manifest.
  - `[low]` `[patch]` Edge Case Hunter: `build_tool_specs()` iterates `tree.body` (top-level statements only) rather than `ast.walk(tree)`, so an `@mcp.tool()` registration nested inside a class or another function would silently vanish from the inventory. Confirmed via direct AST comparison: today's top-level-only scan and a full `ast.walk` both find exactly the same 46 tools, so this has no live effect — but the fix is a one-token swap (`ast.walk(tree)` for `tree.body`) that adds no complexity and restores the more general pattern passes 1-2 already used; a direct correction, not a new guard. Action: patched — confirmed via `grep`.
  - `[low]` `[reject]` Edge Case Hunter: a docstring that is non-empty but reduces to whitespace after `.strip()` would `IndexError` on `doc.strip().splitlines()[0]`. Confirmed via direct scan: no `@mcp.tool` docstring in the live file is whitespace-only; unlikely to ever occur given every tool carries a real one-line summary already.
  - `[medium]` `[patch]` Verification Gap Reviewer: `.claude/tools/mcp_cli_parity.py` (this story's own new file) is absent from both `paths:` filters in `.github/workflows/cfe-regression-net.yml`, the only CI job that runs `test_mcp_cli_tool_parity.py` — confirmed via direct `grep` of the workflow file and of every workflow for `test-ci`/`.claude/tools` references. A commit touching only that file would not trigger the workflow that gates the very test proving the gate works, though in practice a real edit here almost always accompanies a Rule-2 CHANGELOG bump (a watched path). Action: patched — added `.claude/tools/mcp_cli_parity.py` to both `paths:` lists; confirmed via `grep` and that the workflow YAML still parses.
  - `[medium]` `[defer]` Verification Gap Reviewer: no CI path exercises `test_mcp_cli_tool_parity.py` when marshal's `pyforge.marshal.mcp.parity` public surface changes on the marshal side only (`cfe-regression-net.yml` has no `src/shared/packages/pyforge-marshal/**` trigger; `pyforge-station-tests.yml` runs marshal's own suite only). Real cross-package coupling gap, but closing it properly means widening a CI workflow's trigger scope to a sibling package's whole source tree (or adding a marshal-side contract test) — a broader cross-team wiring decision beyond this story's own file, per the reviewer's own filed disposition.
  - `[false]` `[reject]` `carried` Intent Alignment Auditor: re-raises the three-place-rule scope claim for `mcp_cli_parity.py` — same claim and code shape as review passes 1-2's rejected finding (disproof unchanged: `conda_forge_server.py` precedent).
  - `[false]` `[reject]` `carried` Intent Alignment Auditor: re-raises the Rule-2-retro literal-heading-structure claim — same claim and code shape as review pass 1's rejected finding (disproof unchanged: matches this file's own established prose-narrative convention).

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** Mason's 46 `@mcp.tool()` registrations in `.claude/tools/conda_forge_server.py` now
have a CLI↔tool parity gate, extending marshal's `pyforge.marshal.mcp.parity` primitive (never
forked) rather than re-implementing it. `.claude/tools/mcp_cli_parity.py` derives the CLI-verb
surface from every `[feature.*.tasks.*]` pixi table (not one feature alone), anchored at the pixi
**task name** — never the wrapper file's stem — and the tool surface by `ast`-parsing (never
importing) `conda_forge_server.py`'s `@mcp.tool()` registrations. 35 CLI-only verbs and 9 tool-only
tools are each declared in `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES` with a one-line reason; a
`_VERB_OVERRIDE` resolves the one case static analysis can't disambiguate
(`prepare_submission_branch` vs `submit_pr`, both delegating to the identical canonical
`submit_pr.py`). The new `tests/meta/test_mcp_cli_tool_parity.py` proves the live inventory passes
clean and that a fixture-injected mismatch in **each** direction — an on-surface verb with no tool,
a tool with no verb and no allowlist entry, and a stale allowlist entry that's actually claimed —
actually fails the gate, not merely that it runs.

Two implementation attempts were reverted and re-derived after review found genuine scope gaps
(both documented in the Spec Change Log above, not glossed over): attempt 1 anchored verbs at the
wrapper file's stem instead of the pixi task name; attempt 2 anchored correctly but scanned only
the `local-recipes` pixi feature, missing that `vuln-db` also invokes shared CFE wrapper scripts
(concretely, `scan_project` was misfiled as a tool-only asymmetry it was not). The third attempt
closed both gaps; a fourth, lighter pass then applied five review-caught fixes (a duplicated/stale
CHANGELOG paragraph, a dead import, an `ast.walk` robustness restore, a missing stale-entry fixture
test, and a CI `paths:` filter gap for the new file itself) with no further scope issues found.

**Files changed** (final state, three commits: `748d0f1234` `feat(mason):`, `a36082be1c`
`retro(cfe):`, `7c68196881` `retro(cfe):` follow-up):
- `.claude/tools/mcp_cli_parity.py` (new) — the CLI↔tool derivation module.
- `.claude/skills/conda-forge-expert/tests/meta/test_mcp_cli_tool_parity.py` (new) — 9 tests:
  live-inventory pass, tool-count pin, allowlist-reconciliation check, task-name-anchoring
  regression, vuln-db-scope regression, `_VERB_OVERRIDE` regression, and three fixture-injected
  failures (CLI-only-missing-tool, tool-only-missing-cli, stale-allowlist-entry).
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py` — allowlist entry for
  `mcp_cli_parity.py` (a `.claude/tools/` library module, like `conda_forge_server.py`, outside the
  three-place rule's `.claude/skills/conda-forge-expert/scripts/` scope).
- `.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml,reference/mcp-tools.md}`
  — Rule-2 retro: version 8.90.2 → 8.91.0 (MINOR).
- `.github/workflows/cfe-regression-net.yml` — added `.claude/tools/mcp_cli_parity.py` to both
  `paths:` filters so the new file's own CI coverage isn't a blind spot.

**Review findings breakdown** (3 review passes, 58 total individual findings across all layers):
- **Patched** (this pass, pass 3, 5 entries): duplicated/stale `v8.91.0` CHANGELOG+SKILL.md entries
  consolidated (medium); dead `ParityFinding` import removed (low); `build_tool_specs()` restored to
  `ast.walk(tree)` (low); a fixture test added for the stale-allowlist-entry failure direction
  (low); `.claude/tools/mcp_cli_parity.py` added to `cfe-regression-net.yml`'s `paths:` filters
  (medium). All five verified independently after application (direct `grep`/YAML-parse checks plus
  a full re-run of the affected test files and the broader suites below).
- **Deferred** (1): no CI path exercises this test suite when marshal's `pyforge.marshal.mcp.parity`
  public surface changes on the marshal side only — closing it means widening a CI workflow's
  trigger scope to a sibling package's whole source tree, a cross-team wiring decision beyond this
  story's own file. Recorded in frontmatter `deferred:`.
- **Rejected as real-but-low-priority** (pass 1: 10; pass 2: 10 incl. 5 carried; pass 3: 5 incl. 2
  carried) — narrow AST-parsing looseness with zero live trigger today (constant-detection
  operator/operand checks, whole-body verb-reference walk, multi-constant tie-break, bare-decorator
  and `name=`-override forms, missing existence guards on the wrapper dir/tools file/pixi.toml,
  short-form pixi task values, shared task names across features, whitespace-only docstrings, a
  documentation-placement nit, and an unverified cross-file allowlist-reason citation) — each
  confirmed to have no live instance in the current tree, with a fix that would add new guard/branch
  complexity rather than a direct correction.
- **Rejected as false** (pass 1: 3; pass 2: 1 carried; pass 3: 2 carried) — a
  `mcp-tools.md` wording ambiguity (fixed anyway as a bonus low patch, pass 1); the three-place-rule
  applying to `mcp_cli_parity.py` (disproven three times by the `conda_forge_server.py` precedent);
  Rule-2's retro shape needing literal Corrections/Refinements/Additions headings (disproven by this
  file's own established prose-narrative convention, twice); a `recipe-build-docker` allowlist gap
  (disproven — that task's `cmd` never matches the CFE-wrapper regex, so it was never in scope); a
  premature `followup_review_recommended` claim (disproven — that field is recomputed at every
  pass's own Finalize step); and a cross-pass arithmetic-mismatch claim twice (disproven — the two
  compared figures described two different, non-contemporaneous code versions, not a live
  inconsistency).

**Follow-up review recommendation: false.** Two `medium`-severity entries were patched this pass
(the mechanical trigger for `true` on a first pass), but both were independently re-verified after
application — direct `grep`/parse checks confirmed the fix landed exactly as intended, and the full
`pyforge-mason` suite (1577 passed, 2 pre-existing unrelated failures), the full CFE meta suite
(7673 passed, 6 pre-existing unrelated failures), the 9-test parity suite (9/9), and the
`mason_cfe_surface_check.py` detector (clean) all re-ran clean afterward. No specific unverified risk
can be named for either patch, so per the workflow's own rule ("if none can be named, it is
`false`") this is not raised.

**Verification performed:**
- `pixi run -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_mcp_cli_tool_parity.py -v` — 9/9 passed (final state).
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1577 passed, 3 deselected, 2 failed — both pre-existing (baseline commit `57c001c9d7`'s own merge-commit subject trips the CFE-surface-sanctioning guard; unrelated to this story, reproduced identically before any of this story's commits).
- `pixi run -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/ -q` — 7673 passed, 6 failed (all pre-existing: 5 unrelated `sys.path` import bugs in `add_handoff.py`/`inventory_match.py`/`library_futures.py`/`recommend_2027.py`/`universe_sbom.py`, 1 unrelated `test_bmad_artifacts_integrity` "uncovered" spec-classification finding), 3 skipped.
- `python3 scripts/mason_cfe_surface_check.py` — clean, no unsanctioned commit touches the CFE surface.
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/cfe-regression-net.yml'))"` — valid.
- Live allowlist reconciliation (direct script, not just tests): 0 stale `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES` entries, 0 undeclared real asymmetries, `scan_project`/`detail-cf-atlas-vdb`/`inventory-channel` all correctly resolved after the vuln-db scope fix.
- Matrix Test Audit: all 5 I/O-matrix rows (live clean pass; CLI-only fixture fail; tool-only fixture fail; deliberate asymmetry declared with reason; atlas boundary untouched) covered by a passing, ran test.

**Residual risks:** the deferred item above (marshal-side-only API changes aren't CI-exercised
against this gate) is the only known gap, and it's explicitly out of this story's scope per its own
"propose a shared helper to marshal, don't fork" boundary — closing it is a cross-team CI-wiring
decision. The pre-existing `57c001c9d7` merge-commit guard failure in `pyforge-mason`'s test suite
predates this story (from Story 15.2's bmad-loop landing) and is unrelated; it is not this story's
defect to fix and rewriting that shared commit would be destructive.
