---
title: 'Tool-surface rendering and preflight probe'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-1-7-preflight-adapter-config-seeding-and-first-run-acknowledgement.md', '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-1-3-layered-policy-composition-with-provenance-and-validation.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after Epic 6 (S-6.1..6.5 merged)'
---

<intent-contract>

## Intent

**Problem:** AD-43 (the Q-11 resolution) names a gap in the portability claim Epic 6
otherwise makes: a provisioned loop home is reproducible in worktree, backlink,
markers, adapter seed files, and skill-tree projection -- but NOT in which MCP tools
the agent inside it can call. That surface today lives only in the operator's
personal, machine-scoped `~/.claude.json`, which Marshal must never read as authority
or write (the hardest constraint AD-43 states explicitly, and the harness's own
unattended, repeated launches make a silent dependency on a hand-configured file
especially unsafe -- a home cloned to a second machine, or handed to `bmad-loop`
inside a fresh worktree, would launch with a DIFFERENT tool surface than the one an
operator tested against, with no diagnostic).

**Approach:** the project's tool surface becomes a new, closed, STATIC policy key,
`mcp_servers` -- `Mapping[str, {command: str, args?: [str], env?: {str: str}}]`,
composed through the SAME `compose()` fold and the SAME 4-key vocabulary discipline
Story 1.3 established (project -> flags, no fourth layer; default `{}`, "nothing
declared yet" mirroring `epic_surfaces`'/`model_tier_map`'s own empty-mapping
default). `marshal init` (`cli/init.py::run_init`) gains a fifth action -- NOT a sixth
member of `_STEP_NAMES` (see Boundaries & Constraints for why) -- that composes the
project's policy and, when `mcp_servers` is non-empty, renders a project-scoped
`<home>/.mcp.json` (the standard `{"mcpServers": {name: {command, args, env}}}`
shape every MCP-aware client reads) using the EXACT copy-when-absent discipline
Story 1.7's seed-file step already established for adapter config
(`fs.exists(dst)` first; a file already there -- Marshal's own prior render or an
operator's hand edit -- is never touched). `marshal preflight`
(`cli/init.py::run_preflight`) gains a resolvability probe, modeled directly on its
own existing `verify_commands` check (`MRS-PREFLIGHT-006`'s sibling): it reads back
the HOME's OWN rendered `.mcp.json` (never `~/.claude.json`) and, for every server the
COMPOSED POLICY declares, checks whether that file actually carries it and whether its
`command` is resolvable via the same `HarnessPort.binary_present` seam
`verify_commands` already uses (or, for an absolute-path command, `FsPort.exists`).
One new registered code, `MRS-PREFLIGHT-012`, bundles the three sub-cases this probe
can report (missing `.mcp.json` despite declared servers; a malformed/wrong-shaped
`.mcp.json`; a declared server's command not resolvable) -- mirroring
`MRS-PREFLIGHT-008`'s own precedent of bundling closely related "not satisfiably
recorded" sub-cases under one code rather than minting three.

**Resolvability interpretation (Think Before Coding, stated explicitly per the task
brief).** AD-43 says preflight "probes ... resolvability" but does not define the
term for an MCP server the way FR-53 already defines it for `verify_commands`
(`shutil.which`-shaped PATH presence). This spec adopts the narrowest reading
consistent with the existing `verify_commands` precedent and the hard "never touch
`~/.claude.json`" constraint: **resolvable == the server's declared `command` is
findable** -- either on `PATH` (`HarnessPort.binary_present`, the exact same seam
`verify_commands`/the adapter binary check already use) or, if the command string is
an absolute path, present on disk (`FsPort.exists`). This says nothing about whether
the MCP server, once launched, actually SPEAKS the protocol correctly, negotiates a
handshake, or lists any tools -- that would require actually spawning the process,
which is out of scope for a preflight probe (mirrors `verify_commands`' own identical
scope limit: it checks the executable is findable, never that running it succeeds).
This is a narrow, explicit, documented interpretation, not a guess.

## Boundaries & Constraints

- **Never** read or write `~/.claude.json` (or any user-scoped MCP registry) from any
  code path this story touches. The resolvability probe reads ONLY the home's own
  rendered `<home>/.mcp.json`, composed policy, and `PATH`/disk existence.
- **Never** write outside the loop home. `.mcp.json` renders to `<home>/.mcp.json`
  only -- AD-11 target (a), the loop home itself; this is not a new AD-37
  machine-scoped target (that tier is for per-host PROBE RECORDS, not project
  artifacts), so no new write-target enumeration is needed beyond noting the file in
  `run_init`'s own module docstring, matching how the four existing steps and Story
  1.7's seed files are each named there.
- `.mcp.json` render is deliberately NOT a sixth entry in `run_init`'s
  `_STEP_NAMES`/`data.steps` tuple. `_STEP_NAMES` is a narrowly-scoped, well-tested
  invariant (worktree/tier3_backlink/symlink/marker -- the four PROVISIONING
  primitives ported from `scripts/bmad-loop-worktree`/`scripts/bmad-switch`);
  `data.steps` is asserted against by name in multiple existing tests and referenced
  by the module's own docstring as "the four steps". Story 1.7's own seed-file copy
  step set the precedent for how a NEW render/copy action joins `run_init`-family
  commands without perturbing `_STEP_NAMES`: it reports through its own top-level
  `data` key (`data.seed_files`, a list) outside `data.steps`. This story's render
  follows the identical pattern: `data.mcp_json` is a new top-level key on `run_init`'s
  envelope (`{"status": "done"|"skipped"|"failed"}`), sibling to `data.steps`, never a
  member of it.
- Reuses `policy.compose()` verbatim inside `run_init` (mirroring how `run_preflight`
  already composes policy) -- `run_init` gains its own `_read_project_policy`/
  `conventional_project_policy_path` calls, identical to `run_preflight`'s own. A
  `PolicyIOError` reading the project policy file surfaces via the ALREADY-REGISTERED
  `MRS-POLICY-004` (its own `.finding`), exactly as `run_preflight` already handles it
  -- no new code. Any other malformed policy content composes down to the default and
  is reported (MRS-POLICY-001/002/005/006) -- no new codes needed for malformed
  `mcp_servers` policy content; it is validated by the SAME `_merge_field` fold every
  other STATIC mapping-typed key (`model_tier_map`, `epic_surfaces`) already uses,
  under the SAME shared code `MRS-POLICY-002` ("every STATIC field's shape violation
  is MRS-POLICY-002", the module's own documented rule -- extending it, not
  inventing a fourth split).
- `mcp_servers` is NOT exposed via `cli/config.py --set` (mirrors `model_tier_map`/
  `epic_surfaces`/`landing_rules` -- `cli/config.py`'s own documented UX restriction on
  which flags it exposes for list/mapping-typed fields; `compose()` itself still
  layers it uniformly across all 3 layers per AD-16).
- No spawning of any MCP server process, ever, anywhere in this story -- resolvability
  is PATH/disk presence only (see Intent's own "Resolvability interpretation").
- No modeling of the MCP protocol itself (handshake, tool listing, capabilities) --
  out of scope, per the interpretation above.
- Deps: S-1.7 (the adapter-seed pattern this story's render step reuses verbatim) and
  S-6.1 (`cli/adapters.py`'s profile-driven adapter selection -- referenced only as
  the most recent precedent for "a new policy key composed the same way as existing
  ones"; this story adds no dependency on `cli/adapters.py` itself).

## Acceptance Criteria

**Given** a project policy declaring `mcp_servers`
**When** `marshal init <slug>` provisions (or re-provisions) the home
**Then** a project-scoped `<home>/.mcp.json` renders with the declared servers under
the standard `{"mcpServers": {...}}` shape
**And** a second `marshal init <slug>` run against an already-rendered `.mcp.json`
(including one an operator hand-edited) leaves it byte-for-byte untouched
(seed-not-overwrite, identical to Story 1.7's adapter seed files)
**And** a project policy declaring no `mcp_servers` (the default, empty mapping)
renders nothing and reports `data.mcp_json.status == "skipped"`

**Given** a provisioned home with a rendered (or missing, or hand-edited) `.mcp.json`
**When** `marshal preflight <slug>` runs
**Then** it reports, per policy-declared server, whether that server's command is
resolvable (`data.mcp_servers`, mirroring `data.verify_commands`' own shape)
**And** an unresolvable command, a missing `.mcp.json` despite declared servers, or a
malformed `.mcp.json` each produce a blocking `MRS-PREFLIGHT-012` finding
(`Verdict.ERROR`)
**And** no code path in either command reads or writes `~/.claude.json`

## I/O & Edge-Case Matrix

| Input | `marshal init` | `marshal preflight` |
|---|---|---|
| `mcp_servers` empty (default) | `data.mcp_json.status = "skipped"`, no write | `data.mcp_servers = []`, no findings |
| `mcp_servers` non-empty, `.mcp.json` absent | renders it, `status = "done"` | (after init) resolvable servers -> no findings; unresolvable -> `MRS-PREFLIGHT-012` per server |
| `mcp_servers` non-empty, `.mcp.json` already present (Marshal's own prior render OR hand-edited) | untouched, `status = "skipped"` | probes the file AS IT EXISTS, not the policy's own rendering |
| `.mcp.json` write fails (e.g. permission denied) | `status = "failed"`, `MRS-INIT-004`, `Verdict.ERROR` | n/a |
| policy declares servers but `<home>/.mcp.json` missing entirely (init never ran, or file removed by hand) | n/a | `MRS-PREFLIGHT-012`, "does not exist -- run marshal init" |
| `.mcp.json` present but not valid JSON / no top-level `mcpServers` object | n/a | `MRS-PREFLIGHT-012`, malformed-shape message |
| a declared server present in the file but its `command` is not on PATH and not an existing absolute path | n/a | `MRS-PREFLIGHT-012` per server |
| malformed `mcp_servers` value in a policy layer (e.g. a bare string, a spec with an unknown key, empty `command`) | that LAYER's value excluded, `MRS-POLICY-002`, falls through to previous/default | same (via composed `effective.mcp_servers`) |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/policy.py`
  - `_STATIC_KEYS`: add `"mcp_servers"`.
  - `DEFAULT_POLICY["mcp_servers"] = {}` (empty mapping, "nothing declared yet").
  - New validator `_valid_mcp_servers` (mirrors `_valid_model_tier_map`'s/
    `_valid_epic_surfaces`' shape-checking pattern): `Mapping[str, {command: str
    (non-empty), args?: tuple[str, ...] of non-empty str, env?: Mapping[str, str]}]`,
    closed key set per entry (`{"command", "args", "env"}`), non-empty server names.
  - `EffectivePolicy` gains a new public `mcp_servers: PolicyField` attribute, wired
    into `__post_init__`'s field-type loop, `__repr__`'s static tuple, and
    `content_hash`'s payload dict -- same four touch points every existing STATIC
    field already has.
  - `compose()` gains one more `_merge_field(...)` call, same shape as
    `model_tier_map`'s own, under `MRS-POLICY-002`.
- `src/pyforge/marshal/schemas/policy.json`: add `mcp_servers` to `required` and
  `properties` (a `$ref` to the existing generic `#/$defs/policyField`, matching
  every other key's own untyped-`value` convention -- the schema does not deep-type
  `value`'s shape for ANY key today, including the structurally-richer
  `landing_rules`/`model_tier_map`).
- `src/pyforge/marshal/cli/init.py`
  - `run_init`: after the existing marker step, compose the project's policy (same
    `_read_project_policy`/`conventional_project_policy_path`/`policy.compose` calls
    `run_preflight` already makes) and call a new `_render_mcp_json(slug, home,
    effective, fs)` helper; merge its findings and set `data["mcp_json"]`.
  - New `_render_mcp_json` helper: builds the `{"mcpServers": {...}}` JSON, checks
    `fs.exists(dst)` first (copy-when-absent), writes via `fs.write_text_atomic` on
    the miss, reports `"done"`/`"skipped"`/`"failed"`; a write failure appends
    `_op_failed_finding(...)` (the EXISTING `MRS-INIT-004` helper `run_init` already
    uses for every other fs/git operation failure in this function).
  - `run_preflight`: after the existing `verify_commands` block (same section of the
    function, same shape of loop), add an MCP-server resolvability block reading
    `<home>/.mcp.json` via `fs.read_text` and probing each of
    `effective.mcp_servers.value`'s declared servers against `harness.binary_present`/
    `fs.exists`; appends `data["mcp_servers"]` (a list, mirroring
    `data["verify_commands"]`'s own per-entry shape) and `MRS-PREFLIGHT-012` findings.
  - `_render_text_preflight`/`_render_text` (the `--format text` projections): add a
    couple of lines for the new `data` keys, mirroring the existing per-key
    conditionals.
  - Module docstring: a short paragraph naming this story's addition, following the
    file's own per-story docstring-paragraph convention (one paragraph per story that
    touched this module).
- `src/pyforge/marshal/core/findings.py`: register `MRS-PREFLIGHT-012` (docstring
  narrative paragraph for Story 6.9 + `REGISTERED_CODES` entry).
- `src/pyforge/marshal/core/verdict.py`: `_CLASSIFY_TABLE["MRS-PREFLIGHT-012"] =
  Verdict.ERROR` (same tier as `MRS-PREFLIGHT-006`/`008`/`009` -- a real, attempted
  check found or could not confirm a real problem), plus a doc comment.
- Tests: `tests/unit/test_policy.py` (mcp_servers compose/validation/content-hash
  cases, mirroring the existing `model_tier_map` test block), `tests/unit/test_init.py`
  (render + seed-not-overwrite + preflight-probe cases, mirroring the existing
  `seed_files`/`verify_commands` test blocks), `tests/meta/` codes/classification
  completeness tests pick up the new code automatically (no new meta-test file
  needed -- they already enumerate `REGISTERED_CODES`/`_CLASSIFY_TABLE`).

## Design Notes

- **Why `mcp_servers` is STATIC, not SEED.** Like `model_tier_map`/`epic_surfaces`, it
  is project/policy-declared and never narrowed at runtime by a journal entry --
  there is no notion of "the live MCP tool surface during a run" distinct from what
  policy composed at provision time. SEED is reserved for fields the journal fold
  actually narrows (AD-26); this field has no such consumer.
- **Why `.mcp.json` renders in `init`, not `preflight`.** The AC states this
  explicitly (render on provision, probe on preflight) and it matches the existing
  division of labor: `run_init` is the sole writer of loop-home structure (AD-11
  target (a)); `run_preflight` is read-only-plus-seed-copy (Story 1.7's own adapter
  seed files are the one write preflight performs, and even those are copy-when-absent
  from a KNOWN main-checkout source path -- not policy-rendered content). Rendering
  policy-declared content is closer in kind to `run_init`'s existing marker/symlink
  writes (deriving bytes from the composed slug/policy) than to preflight's
  copy-from-known-source seed step, so it belongs in `run_init`.
- **Why one bundled code (`MRS-PREFLIGHT-012`) instead of three.** Mirrors
  `MRS-PREFLIGHT-008`'s own precedent exactly (its docstring: "all three are 'the
  first-run gate is not satisfiably recorded'"). All three MCP sub-cases here are
  the same underlying fact from the operator's point of view: "the declared tool
  surface is not fully resolvable" -- naming three codes for one actionable fact
  would only fragment `_CLASSIFY_TABLE` without adding diagnostic value (the
  message text already distinguishes the sub-case).
- **Why resolvability reads the HOME's rendered file, never `~/.claude.json`.** This
  is the story's hardest constraint, stated in the task brief and in AD-43 itself.
  Reading the home's OWN `.mcp.json` (a file only Marshal or the operator, scoped to
  THIS project's home, ever writes) keeps the probe entirely within AD-11's write/read
  boundary and matches the AC's own framing: "a provisioned home is reproducible in
  the one respect it currently is not" -- the fact being verified is about the HOME's
  own portable state, not the operator's personal global registry.
- **Seed-not-overwrite mechanism reused verbatim.** `_render_mcp_json` uses the exact
  same `fs.exists(dst)` gate `run_preflight`'s seed-file loop already uses -- not a
  new mechanism, a second call site of the identical one-line check.

## Verification

- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (full suite, not the filtered default task).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`.
- Manual trace: construct a fake `FsPort`/`HarnessPort` pair (matching existing test
  doubles in `tests/unit/test_init.py`) exercising (1) first `init` renders
  `.mcp.json`, (2) a second `init` after hand-editing the file leaves it byte-for-byte
  untouched, (3) `preflight` against an unresolvable declared command produces
  `MRS-PREFLIGHT-012` and `Verdict.ERROR`, (4) neither test double is ever asked to
  read or write a path resembling `~/.claude.json`.

## Review Triage Log

Self-review pass (adversarial, post-implementation, 2026-08-07). Findings and
disposition:

1. **P1 (fixed before landing) -- `test_init_mcp_json_write_failure_reports_finding`
   as first drafted was not testing what it claimed.** `FakeFs.fail_write_text` is a
   single global flag, not path-specific, so setting it before a FIRST `run_init`
   call breaks the marker-write step (which runs before the mcp.json render) --
   the test still asserted `MRS-INIT-004 in out` and passed, but for the WRONG
   reason (a marker-write failure, not an mcp.json-write failure). Fixed by
   restructuring the test as a two-run sequence: a first, clean run converges
   worktree/tier3_backlink/symlink/marker to `skipped` (still no `mcp_servers`
   declared), THEN the policy is monkeypatched to declare a server and
   `fail_write_text` is set only for the second run -- by that point the four
   provisioning steps are already convergent no-ops, so the mcp.json render is the
   only write left to attempt, and the finding genuinely traces to it.
2. **Verified: no code path reads or writes `~/.claude.json`.** Grepped
   `cli/init.py`/`core/policy.py` for `.claude.json`/`Path.home()` -- the only
   matches are doc-comment prose citing the constraint; neither `_render_mcp_json`
   nor `_probe_mcp_servers` calls `Path.home()` or references any path outside
   `home`/the composed policy. Added a dedicated test,
   `test_preflight_mcp_probe_never_touches_user_scoped_registry`, asserting no path
   FakeFs was ever asked to read/write contains `.claude.json`.
3. **Verified: seed-not-overwrite genuinely holds across a second `marshal init`
   run, including an operator hand-edit.** `test_init_second_run_does_not_overwrite_
   hand_edited_mcp_json` renders once, then overwrites the fake's in-memory
   `.mcp.json` bytes to a hand-edited value, re-runs `init`, and asserts BOTH zero
   new `write_text_atomic` calls AND the hand-edited bytes survive unchanged --
   the two-part check a "status reports skipped but a write happened anyway" bug
   could otherwise pass with only the first half asserted.
4. **Considered and rejected: minting a distinct code per MCP sub-case
   (missing/malformed file, unresolvable command).** Would fragment
   `_CLASSIFY_TABLE`/`REGISTERED_CODES` for a distinction the operator-facing
   message text already carries losslessly; `MRS-PREFLIGHT-008` already
   established the "bundle closely related sub-cases under one code" precedent
   this story follows. No change.
5. **Considered and rejected: making the render step a fifth `_STEP_NAMES`
   member.** Would touch a narrowly-scoped, well-tested invariant (`data.steps`
   asserted by name across many existing tests) for no benefit the sibling
   `data.mcp_json` key doesn't already provide, and breaks the Story-1.7 seed-file
   precedent of reporting through an independent top-level `data` key. No change.
6. **No findings on the resolvability interpretation itself.** The
   PATH/absolute-path-existence-only reading (documented in Intent) was applied
   consistently in both `_render_mcp_json`'s render and `_probe_mcp_servers`'s
   probe; no test or code path implicitly assumed a stronger guarantee (e.g. that
   the server actually speaks MCP).

No corrections to `core/policy.py`'s existing composition machinery were needed --
`_valid_mcp_servers` reused every existing pattern (`_valid_str_tuple` for `args`,
the closed-key-set-per-entry check `_valid_landing_rule` already established)
without any adaptation.

</intent-contract>

### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context.

- `medium` `patch` **Relative commands containing a path separator bypassed the PATH-vs-absolute-path contract via `shutil.which`'s cwd-relative fallback.** `_probe_mcp_servers` delegated every non-absolute `command` to `harness.binary_present` (`shutil.which`), but `shutil.which` does NOT search `PATH` for a name containing a separator -- it checks the literal path relative to the process's OWN cwd instead. A declared command like `"bin/atlas-mcp"` was neither a bare PATH-lookup name nor an absolute path, yet could report `resolvable=True` or `False` depending purely on `marshal preflight`'s invoking cwd -- non-deterministic and silently contradicting the probe's own documented "PATH or absolute path" contract. Fixed: a relative command containing more than one path part is now rejected outright (`resolvable=False`) rather than delegated to `binary_present`; only a bare single-segment name reaches the PATH lookup. New test: `test_preflight_mcp_server_relative_command_with_separator_never_resolvable`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` -- **3055 passed** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by a dedicated regression test.
