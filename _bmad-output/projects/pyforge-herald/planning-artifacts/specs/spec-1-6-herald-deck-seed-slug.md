---
title: 'herald deck seed <slug>'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 1's foundation (transport port + both adapters, bridge-core skeleton, state,
errors, registry) is complete but wired to nothing -- `cli.py`'s `deck` subparser group is still
empty (Story 1.1's deliberate scope), and `deck_pipeline.py` (bridge.py's own docstring names it
as the future home of each CAP function) does not exist. CAP-1's success signal ("From a clean
state, `herald deck seed <slug>` yields a Design project whose prototype, read back, passes the
repo's extract and build; seeding over existing Design-side edits is refused with a structured
conflict and writes nothing") is otherwise unreachable.

**Approach:** Implement `bridge-protocol.md` § *Seed* steps 1-8 as `deck_pipeline.seed`, the first
CAP function to land in bridge-core, composed with `bridge.run` and wired to `herald deck seed
<slug>` via `cli.py`'s first `dispatch`-routed subcommand. Conflict detection is pre-flight
(state.py, then registry.py as a bootstrap fallback for the four hand-seeded pilot decks) rather
than write-response-based, since Story 1.2's own deferred-work ledger (DW-1-2-5) records that the
live conflict wire shape is still unpinned.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.seed(transport, *, slug, repo_root, support_source_project_id=PILOT_SUPPORT_SOURCE_PROJECT_ID, state_path=None, prover=None) -> SeedResult`
  follows `bridge-protocol.md` § Seed exactly: prove locally -> mandatory `get_design_prompt` gate
  -> `create_project` -> `finalize_plan` (all three write paths) -> `create_support_js` ->
  `copy_files` (deck-stage.js from the pilot/override source project) -> `write_files` (the exact
  local prototype bytes that passed the prove step) -> record in both `state.py` (operational) and
  `registry.py` (human-readable, README § *Design project*).
- **Conflict detection runs entirely before any transport call, satisfying "writes nothing" by
  construction:** `state.read` first (the operational source of truth); if that finds nothing,
  `registry.read` against the deck's own README as a bootstrap fallback (exactly what
  `registry.py`'s own module doc names Story 1.6 as the wirer of) -- both raise `SeedConflictError`
  on a hit. A malformed registry section (DW-1-5-1: true of all 13 pre-existing decks) also refuses
  -- "cannot parse the existing link" is not "no link exists".
- `deck_pipeline.py` joins the `bridge.py`-style (laxer) half of the determinism boundary: it may
  import `transport.base` (for `DesignTransport`'s type annotation and the real
  `MODERNIST_DESIGN_SYSTEM_ID` value) but never a concrete adapter, never an inference SDK package,
  never dynamic-import machinery -- `test_bridge.py`'s existing derived denylists sweep it once
  added to `_BRIDGE_CORE_MODULES`, with no denylist itself needing an edit.
- **The `MODERNIST_DESIGN_SYSTEM_ID` import inside `seed` is lazy (inside the function body, not
  module-level).** Resolving `transport.base` as a submodule runs `transport/__init__.py`, which
  eagerly imports every concrete adapter -- a module-level import would mean merely `import
  pyforge.herald.deck_pipeline` loads `McpTransport`/`AgentSdkTransport` into `sys.modules`, the
  exact side effect `bridge.py`'s own `TYPE_CHECKING`-only import exists to avoid. Proven by an
  analogous subprocess probe to `bridge.py`'s own
  `test_importing_bridge_does_not_load_the_transport_package`.
- `MODERNIST_DESIGN_SYSTEM_ID` moves from `mcp_transport.py` to `transport/base.py` (pure
  relocation, still re-exported at the package root unchanged) -- it is a bridge-protocol
  convention every adapter *and* bridge-core need, and only `transport.base` is reachable from
  bridge-core.
- `cli.py`'s `deck seed <slug>` subcommand is the first consumer of `dispatch` (Story 1.4 shipped
  it unwired). `main` builds the V1-default `McpTransport` **inside** the `operation` closure
  passed to `dispatch`, not before -- so a hypothetical construction failure is caught by the same
  AD-6 boundary as everything else, not left to crash `main` raw.
- The local-prove step (CAP-1 step 1: `npm run extract` + `npm run build`) goes through an
  injectable `LocalProver` seam (`prove(deck_dir) -> None`, raising `HeraldError`), mirroring Story
  1.3's process-launch-seam pattern -- the real `NpmLocalProver` is never invoked by this package's
  own tests.
- The local prototype path convention (`bridge-protocol.md` § Conventions) is honoured exactly:
  `presentations/<slug>/project/PyForge <Persona>.dc.html`, persona derived from the slug
  (`pyforge-<name>` -> Title-cased `<name>`; a judgment call for slugs this convention was not
  written for -- see Design Notes).

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No `pull`/`status`/`watch` CLI wiring (Epics 2-4) -- the `deck_subparsers` group stays open for
  them, one at a time.
- No write-level conflict detection from an unpinned wire shape (DW-1-2-5; recorded as DW-1-6-1,
  out of scope) -- the pre-flight check is the whole of this story's conflict-detection surface.
- No change to `McpTransport`'s or `AgentSdkTransport`'s own class structure or public behavior.
- No live network in the default test gate -- every `deck_pipeline`/`cli` test injects a fake
  transport, fake prover, or monkeypatches `deck_pipeline.seed` itself (CLI-layer tests); the
  autouse `deny_network` fixture is still the backstop for anything that somehow reached
  `McpTransport`'s real call path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | fresh slug, local prototype present, no prior state/registry | 8-step sequence in order; `SeedResult` returned; state + registry recorded | No error |
| Missing deck directory | no `presentations/<slug>/` | refused before any call | `HeraldError` |
| Already seeded (state) | `state.read` returns a `DeckState` | refused before any call | `SeedConflictError` |
| Already seeded (registry fallback) | no state entry, well-formed README section | refused before any call | `SeedConflictError` |
| Malformed registry section | no state entry, README section present but not 2-line canonical | refused before any call | `SeedConflictError` |
| Missing local prototype | no `project/PyForge <Persona>.dc.html` | refused before proving | `HeraldError` |
| Local prove fails | `prover.prove` raises | propagated before any transport call | `HeraldError` |
| Empty design-system prompt | `get_design_prompt` returns `""` | refused before `create_project` | `HeraldError` |
| `finalize_plan` etags present | `base_etags` names a path | that etag used as `if_match` | No error |
| `finalize_plan` etags absent | `base_etags` omits a path | `"0"` (fresh) used as `if_match` | No error |
| `copy_files` source project | default | `PILOT_SUPPORT_SOURCE_PROJECT_ID` | No error |
| `copy_files` source project override | `support_source_project_id=...` | override value used | No error |
| CLI success | `herald deck seed <slug>` | exit 0; stdout names the slug + the project url | No error |
| CLI `HeraldError` | `deck_pipeline.seed` raises | one stderr line; exit per `errors.exit_code_for` | per error type |
| `herald deck seed` (no slug) | argparse | usage error | exit 2 |
| `herald deck seed --help` | argparse | help text | exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- create -- CAP-1
  `seed`, `SeedResult`, `LocalProver` (Protocol) + `NpmLocalProver`, `_persona_from_slug`,
  `PILOT_SUPPORT_SOURCE_PROJECT_ID`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck seed <slug>`
  subparser (`--repo-root`, `--support-source-project`), `_run_deck_seed`, `main` now retains
  `args` past the `SystemExit` catch and routes on `command`/`deck_command`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` -- edit --
  `MODERNIST_DESIGN_SYSTEM_ID` relocated here from `mcp_transport.py` (pure move).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py` -- edit --
  import-only change following the relocation above.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/__init__.py` -- edit -- source
  `MODERNIST_DESIGN_SYSTEM_ID` from `.base` instead of `.mcp_transport` (re-export unchanged).
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- create -- the I/O matrix's
  `deck_pipeline` rows, `FakeTransport`/`FakeProver` (hand-written), `NpmLocalProver`'s own
  error-mapping tests (`subprocess.run` patched, nothing spawned).
- `src/shared/packages/pyforge-herald/tests/test_cli_seed.py` -- create -- the I/O matrix's CLI
  rows; `deck_pipeline.seed` monkeypatched so only the CLI's own composition is under test.
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- `deck_pipeline` added to
  `_BRIDGE_CORE_MODULES`; a new parametrized test folds `bridge.py`'s
  "reaches transport only via transport.base" check over both `bridge` and `deck_pipeline`; a new
  subprocess probe proves importing `deck_pipeline` alone does not load the transport package;
  `test_derived_adapter_denylists_cover_the_known_adapter` gains assertions for Story 1.3's
  `agent_sdk_transport`/`AgentSdkTransport` (already covered by the derived sets, just newly
  pinned).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` -- edit --
  DW-1-5-1 updated (the anticipated "seed migrates it" resolution changed to "seed refuses and
  requires manual resolution"); new `DW-1-6-1` records the write-level-conflict-detection scope
  limit.

## Design Notes

**Why the registry-bootstrap-fallback conflict check exists at all.** Without it, re-running
`herald deck seed` against any of the four pilot decks (marshal, herald, mason, doctor -- seeded by
hand 2026-07-23, before `state.py` existed) would silently create a *second* Design project for an
already-linked deck: `state.read` finds nothing (no state file existed at pilot time), so a
state-only check would sail straight through. `registry.py`'s own module docstring names this exact
wiring point ("this section is the human-readable registry, wired in as a bootstrap fallback only
by a later story ... Story 1.6+"), so this is not a speculative addition -- it is the story that
docstring was written to be fulfilled by.

**Judgment call: a malformed registry section refuses rather than migrates.** DW-1-5-1 speculated
`register()`'s idempotent replace-in-place might let `seed`'s final `registry.register` call
"naturally migrate" the 13 pre-existing malformed sections to the canonical shape. Implemented
instead: the *conflict check* runs before any write, and a present-but-unparseable section there
is treated as "already linked, cannot verify the details" rather than "nothing registered yet" --
overwriting a link this module cannot prove matches its own canonical shape risks silently
clobbering a real, hand-verified project id if the parse failure happens to mask a different one.
The migration debt is real and unresolved (`DW-1-5-1`'s status updated, not closed); a future story
can add an explicit `--force`/`--migrate-registry` escape hatch if that debt needs paying down
through this CLI rather than by hand.

**Judgment call: `_persona_from_slug` is a mechanical derivation, not a lookup table.** No
persona-name registry exists anywhere in this repo's code (only in prose: presentation-deck
READMEs, `bridge-protocol.md`'s Conventions). `pyforge-<name>` -> Title-cased `<name>` matches every
existing single-word persona (Warden, Marshal, Herald, Doctor, Mason, Atlas, Scribe, Genesis,
Steward) exactly. A multi-word or prefix-less slug (a future non-`pyforge-` deck, or a compound
name like a hypothetical `pyforge-cli-anything-hub`) gets a readable but unverified guess rather
than a refusal -- narrower than inventing a lookup table this repo has no source of truth for, and
wide enough that a wrong guess is a visible, correctable README/Design-project *name*, never a
silent data-loss path.

**Judgment call: `PILOT_SUPPORT_SOURCE_PROJECT_ID` pins a specific project, not "any prior deck".**
CAP-1 step 6 needs *some* already-seeded project to copy `deck-stage.js` from -- the bootstrap
dependency every first seed has. `bridge-protocol.md` § Pilot evidence names four candidates; the
already-seeded `pyforge-marshal` project is picked as the default (documented, evidenced, and the
same project `registry.py`'s own module docstring cites), overridable per call via
`--support-source-project` for an operator who prefers a different source.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- 346 passed, 2 skipped (was 311 passed, 2
  skipped after Story 1.3; +35 net new tests this story across `test_deck_pipeline.py`,
  `test_cli_seed.py`, and the `test_bridge.py` extensions).
- `ruff format --check` / `ruff check` from the package root -- clean on every file this story
  touches; pre-existing findings elsewhere (import ordering in `test_bridge.py`/`test_registry.py`,
  `SIM117`/`FURB188` in `mcp_transport.py`/`base.py`) are untouched and out of scope.
- `herald deck seed --help` -- exit 0, argparse-generated help naming `slug`, `--repo-root`,
  `--support-source-project`.
- `herald deck seed` (no slug) -- exit 2 (usage error).

**Manual checks:**
- `grep -n "MODERNIST_DESIGN_SYSTEM_ID" transport/base.py transport/mcp_transport.py` confirms the
  relocation: defined once in `base.py`, referenced (not redefined) via import in `mcp_transport.py`.
- `python -c "import sys, pyforge.herald.deck_pipeline; print(any(m.startswith('pyforge.herald.transport') for m in sys.modules))"`
  prints `False` -- merely importing `deck_pipeline` loads no adapter.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Same caveat as Story 1.3's own entry: implemented and reviewed by one session, not the two-pass
independent-reviewer loop earlier stories went through under `bmad-loop`. Findings below are from a
deliberate adversarial re-read after the suite was green, looking for: exception handling too
broad/narrow, resource leaks, silent failures that should be loud, and docstring/behavior
mismatches.

- `[high]` `[patch]` **The registry-bootstrap-fallback conflict check was missing entirely from the
  first implementation.** The original `seed` gated only on `state.read`, which is empty for all
  four hand-seeded pilot decks (pyforge-marshal/herald/mason/doctor) -- re-seeding any of them
  through this CLI would have silently created a duplicate Design project, exactly the failure mode
  `registry.py`'s own module docstring names Story 1.6 as responsible for closing ("wired in as a
  bootstrap fallback only by a later story ... Story 1.6+"). Found while writing this spec's own
  Design Notes and cross-checking `registry.py`'s docstring claim against the actual conflict-check
  code -- the claim and the code disagreed. Added the `registry.read` fallback (including the
  malformed-section refusal), three new tests, and `DW-1-5-1`/`DW-1-6-1` ledger updates.
- `[medium]` `[patch]` **`MODERNIST_DESIGN_SYSTEM_ID` was imported from `.transport.base` at
  module level**, which -- because resolving a submodule runs its package's `__init__.py` --
  transitively loaded `McpTransport`/`AgentSdkTransport` into `sys.modules` merely from `import
  pyforge.herald.deck_pipeline`. This defeats the purpose of `bridge.py`'s own carefully
  `TYPE_CHECKING`-only import, which exists precisely so "the boundary holds in `sys.modules`, not
  only in this file's AST" (that file's own docstring). Moved the import inside `seed`'s function
  body (a lazy import, still caught by the AST-based determinism-boundary check, which walks the
  whole tree regardless of nesting); added a subprocess-probe test analogous to `bridge.py`'s own.
- `[low]` `[patch]` **`cli.py` constructed `McpTransport()` before calling `dispatch`**, so a
  hypothetical construction failure would have crashed `main` raw instead of going through the AD-6
  stderr/exit-code boundary every other failure in this call does. `McpTransport.__init__` cannot
  actually fail on its no-argument default today, so this was latent, not reachable -- moved the
  construction inside the `operation` closure anyway, since the cost is zero and the boundary
  guarantee should not depend on today's implementation staying that way.
- `addressed_findings`: 3 (1 high, 1 medium, 1 low). No `intent_gap`, no `bad_spec`, no `defer`
  beyond the two items already recorded in `deferred-work-ledger.md` (DW-1-6-1's write-conflict
  scope limit, and DW-1-5-1's still-open migration debt), no `reject`. The high-severity finding
  (missing registry fallback) is the kind of gap the story's own module docstring should have made
  impossible to miss on a first read -- it was caught here by cross-checking the spec's own Design
  Notes against the code before finalizing, not by a second reviewer. That a single-agent pass
  needed a second cross-check to surface a high-severity gap at all is why
  `followup_review_recommended: true` is set above -- a genuine independent review pass is still
  warranted here, even though this pass's own findings were all patched, not merely noted.

All three patches applied; full suite re-verified green after patching: **346 passed, 2 skipped**;
`ruff format --check` and `ruff check` clean on every file this story touches.

### 2026-08-07 -- Epic 1 close-out adversarial review (Blind Hunter + Edge Case Hunter, parallel, no shared context) -- the genuine independent review pass this spec's own `followup_review_recommended: true` called for
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` (Blind Hunter) **A mid-pipeline transport failure orphaned a duplicate
    Design project on retry.** `state.write`/`registry.register` only ran after ALL of
    `finalize_plan`/`create_support_js`/`copy_files`/`write_files` succeeded. Any of those four
    (an etag conflict, a network error, a malformed plan response -- all realistic
    `TransportCallError`/`TransportUnreachableError` paths) raising left the already-created remote
    project completely untracked by state.py's own conflict gate (`seed`'s FIRST check). A retry
    passed both `state.read`/`registry.read` cleanly and called `create_project` AGAIN -- exactly
    the double-project-creation failure mode the earlier self-review pass (above) believed it had
    closed via the registry-fallback fix, which only protects the "hand-seeded before state.py
    existed" bootstrap case, not any failure between `create_project` and the final state/registry
    writes. Fixed: `state.write` now runs immediately after `create_project` succeeds, before
    `finalize_plan` -- the SAME unconditional `etags={}`/`last_pull=None` payload this call always
    wrote, just earlier, so a retry's own first conflict check now sees it regardless of where a
    later step fails. New test:
    `test_seed_records_state_immediately_so_a_mid_pipeline_failure_never_duplicates_the_project`
    (injects a `finalize_plan` failure via a new `FakeTransport(fails={...})` seam, asserts the
    project was created + recorded, then asserts a fresh `seed()` call refuses rather than calling
    `create_project` a second time).
  - `[medium]` `[patch]` (Edge Case Hunter) **A missing `README.md` let the pipeline run all the
    way to a real project creation before failing.** `registry.read(readme_path)` (the pre-flight
    conflict check) tolerates a missing README (`FileNotFoundError` -> "nothing registered yet"),
    but `registry.register` (called at the very end) refuses outright against one -- "this module
    never fabricates a whole README from nothing." The old sequence: create the project, populate
    it, `state.write` succeeds (recording it seeded), THEN `registry.register` raises. The CLI
    reported a hard failure while a real, populated project existed and state.py called the slug
    permanently seeded, with no way to complete registration short of a manual `registry.register`
    call or hand-authoring the README -- and (compounding with the finding above, now fixed) a
    retry would have hit `SeedConflictError` rather than ever getting a chance to finish. Fixed: a
    pre-flight `readme_path.is_file()` check now runs before ANY transport call (before even the
    local prover), consistent with this function's own "writes nothing before every precondition it
    can check without I/O" design. New test:
    `test_seed_refuses_a_missing_readme_before_any_transport_call`. One existing test
    (`test_seed_refuses_a_missing_local_prototype_before_proving`) needed a README added to its
    fixture, since it was deliberately testing prototype-absence and the new, earlier README check
    would otherwise mask that scenario.

**Follow-up review recommendation: false** -- both findings are isolated to the seed pipeline's own
write-ordering and pre-flight-check sequencing, each covered by a dedicated new test proving the
fix; this pass is the independent review the prior self-review pass explicitly asked for, and it
surfaced exactly the class of gap (partial-failure state consistency) that a same-agent self-review
is structurally least likely to catch on its own.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- **349 passed, 2 skipped** (whole-package total, incl. Story 1.3's own
close-out patch landed in the same pass); `ruff format --check`/`ruff check` clean.
