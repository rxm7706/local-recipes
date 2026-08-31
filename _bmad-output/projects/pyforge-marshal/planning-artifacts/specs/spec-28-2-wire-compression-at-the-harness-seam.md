---
title: 'Wire compression at the harness seam (Story 28.2, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: '07da273ba7c52228e23cb26cf72148ac59151b20'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - headroom-ai is ACTIVE in pixi since 2026-08-30 (0.37.0, all platforms — the
    pixi-candidate-currency click wall fell; `headroom` CLI verified live). The seam must
    STILL be fully testable with an injectable wrapper and degrade gracefully when the
    instrument is absent (non-linux fleets, future regressions) — availability changed,
    the design constraint did not.
deferred:
  - summary: >-
      The bmad-loop engine (`marshal factory spin`) is never wrapped; an enabled wire
      layer only reports its own inapplicability there.
    evidence: |-
      Marshal launches `bmad-loop run` on that engine and bmad-loop, not marshal,
      launches the coding CLI, so this seam has no argv to prefix. Confirmed reachable
      rather than impossible: bmad-loop's `adapters/profile.py` exposes `binary` /
      `launch_args` / `env`, `.bmad-loop/profiles/*.toml` is an overlay marshal already
      reads, and marshal already writes into the loop home at spin time. The missing
      piece is a loop-home-provisioned launcher shim, which epics.md places in Story
      28.3 ("Genesis seeds the token-economy kit ... verifies caveman-skill deployment,
      CCR store dir"). Mitigating: `factory dispatch --fleet` is the drain engine, and
      it IS wrapped.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
    severity: medium
  - summary: >-
      Two concurrent wrapped dispatches share the first launcher's proxy and therefore
      its CCR store, so the second session's store is not inside its own loop home.
    evidence: |-
      `headroom wrap` defaults to port 8787 and attaches to an already-running proxy
      instead of starting a second one; reused-proxy settings come from the first
      proxy's process environment, including `HEADROOM_WORKSPACE_DIR`. Tearing down the
      first worktree then removes the store out from under the others. Verified that
      this is NOT scopable through the declarative `[wrapper.env]` surface: `wrap
      claude`'s `--port` is a plain `click.option(default=8787)` with no `envvar=`
      binding (unlike `headroom proxy`'s), so a per-launch port would need argv-level
      templating the current prefix schema cannot express. Documented as an operator
      caveat in `claude.toml`; not detected or reported at runtime, so
      `data["wire"].store_dir` can name a directory the session is not using.
      Blast radius today is zero — the layer ships disabled by default.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
    severity: medium
  - summary: >-
      `factory spin` composes policy without the repo-defaults layer, so a repo-wide
      `[context.wire]` is invisible AND unreported there while dispatch acts on it.
    evidence: |-
      `cli/dispatch.py::_compose_policy` folds in `read_repo_policy_defaults()`;
      `cli/spin.py`'s `policy.compose(project_slug=slug, project=..., flags={})` does
      not. A `[context.wire] enabled = true` in `_bmad-output/policy-defaults.toml`
      therefore wraps a factory dispatch and produces neither a wrap nor an
      `MRS-SPIN-017` on spin — the silent no-op this story set out to eliminate. The
      asymmetry PRE-DATES this story (the same shape feeds Story 28.1's
      `render_policy_toml` block); this change is what makes it produce a wrong report.
      Fixing it properly changes resolution for all 30 policy keys on spin, which is
      out of proportion to this seam. No test covers the repo-defaults layer for
      `[context]` on either engine.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
    severity: medium
  - summary: >-
      A `[wrapper]` may legally declare no store at all, in which case headroom falls
      back to a user-global `~/.headroom` workspace.
    evidence: |-
      `store_env`/`store_relpath` are validated both-or-neither, and both-absent is
      deliberately blessed (`test_wrapper_may_declare_neither_store_field`). For a
      headroom-shaped wrapper that means `HEADROOM_WORKSPACE_DIR` is left unset and the
      CCR store accumulates in a user-global cache — precisely what the loop-home
      scoping AC exists to prevent. `test_every_packaged_wrapper_is_reversible_and_loop_home_scoped`
      enforces the invariant for packaged profiles only; overlays go through the same
      validator and get a pass. Left open deliberately: the Approach also names a
      "transparent proxy for base-URL-only tools" form that may legitimately have no
      store, so making the store mandatory now could foreclose it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
    severity: low
  - summary: >-
      `aggressiveness` is resolved, journaled and echoed on both engines but changes
      nothing about the launch.
    evidence: |-
      No mapping to any wrapper knob exists — no rung-specific argv token, no
      rung-specific env. An operator reading `wire: applied=True aggressiveness=high`
      will reasonably conclude a rung took effect. The graduated ladder is epics.md
      Story 28.6 (token-economy CAP-?), so the value is declaration-only until then;
      the payload does not say so.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
    severity: low
  - summary: >-
      A wrapped launch prepends the resolved CLI's whole directory to the child PATH,
      widening resolution beyond what the unwrapped launch had.
    evidence: |-
      Wrapping replaces the absolute binary path with the wrapper prefix, so the CLI
      must be findable on PATH; the adapter prepends its directory. For the pixi-env
      case that puts every executable in `.pixi/envs/local-recipes/bin` ahead of the
      operator PATH for the whole agent session and everything it shells out to. The
      comment claims "exactly the reachability the unwrapped launch already had, and
      nothing more", which is true for the CLI and false for its neighbours. A
      per-launch symlink shim would deliver the stated minimality.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
    severity: low
  - summary: >-
      The journal records that a session was wrapped but not what wrapped it.
    evidence: |-
      `WireWrap.journal_payload()` emits `applied`/`reason`/`store_dir`/`aggressiveness`;
      neither the resolved wrapper binary path nor the launch argv is journaled. The
      wrapper version and invocation shape — the things that determine actual savings —
      are unrecoverable after the fact, which epics.md Story 28.5 (the pinned
      wrapped-vs-unwrapped benchmark, deps S-28.2 + S-28.3) will need.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
    severity: low
  - summary: >-
      The new ignore-rule meta-test hardcodes the store path instead of deriving it from
      the packaged wrapper's `store_relpath`, so the two can still drift apart.
    evidence: |-
      Partly closed during this review pass: `tests/meta/test_wire_store_ignored_not_the_seed_namespace.py`
      now asserts effective `git check-ignore` behaviour in both directions (store
      ignored, seed namespace not), which is the right shape and mirrors
      `test_skill_projection_manifest_untracked.py`. What remains is that the path is a
      module-level literal rather than `load_packaged_profiles()["claude"].wrapper.store_relpath`,
      so relocating the store in the TOML would leave the test passing against a path
      nothing uses while the real store lands unignored — re-dirtying every loop
      worktree, which is the failure the ignore rule exists to prevent.
    location: >-
      src/shared/packages/pyforge-marshal/tests/meta/test_wire_store_ignored_not_the_seed_namespace.py
    severity: low
  - summary: >-
      The `HEADROOM_MODE = "cache"` pin is silently not honoured when `wrap` attaches to
      an already-running proxy.
    evidence: |-
      `cli/wrap.py:658-661` forwards `HEADROOM_MODE` into `--mode` only inside the
      start-a-proxy path; the reuse path returns early after comparing only
      memory/learn/code-graph/backend/api-url, so the mode is never checked or reset.
      An operator with a `token`-mode proxy already listening gets marshal's wrapped
      session routed through the prompt-prefix-rewriting mode the spec lists under
      Block If (NFR-14). The same reuse path means `--code-memory none` does not
      prevent attaching to a proxy someone else started with `--memory`. Same root
      cause as the shared-proxy entry above.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Every tool output, log, and file read a session makes crosses the wire
uncompressed — the dominant, unbounded per-iteration token sink. Marshal's harness profiles
launch the coding CLI bare.

**Approach:** Harness profiles gain an optional wrapper field (e.g. `headroom wrap <cli>` /
transparent proxy for base-URL-only tools), applied at spin/dispatch when the `[context]`
wire layer is enabled (Story 28.1's block). The CCR (compress-cache-retrieve) store is
loop-home-scoped, torn down with the worktree. The wrapper is injectable so the seam is
testable without the real instrument.

## Acceptance Criteria

- Given an enabled wire layer, when spin/dispatch launches a session, then the launched
  command is demonstrably wrapped (profile-resolved, journal-visible) and the CCR store path
  is inside the loop home.
- Given a compressed artifact in the CCR store, when retrieved, then it is byte-exact to the
  original.
- Given identical inputs wrapped vs unwrapped, when the provider call is composed, then the
  prompt prefix (system prompt, tool definitions, older turns) is byte-identical — proven by
  a prefix byte-comparison test.
- Given the instrument is unavailable (not installed, platform gap), when a run launches,
  then the layer disables with a named finding and the run proceeds unwrapped — never a
  blocked run, never a silent no-op.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-2-wire-compression-at-the-harness-seam`.

**Block If:** A change would compress the story spec/ACs/gate verdicts/escalation context,
rewrite the prompt prefix (NFR-14 violation), or wire the BSL-1.1 `@caveman-ai/cli` proxy.

**Never:** Silently-lossy compression (reversible-or-absent). A second gate verdict. Editing
`pixi.toml` to force-activate headroom-ai (that unblock belongs to pixi-candidate-currency).
Enabling headroom's cross-agent SharedContext memory feature — a second memory
store-of-record by the back door; Scribe's capture/recall (`.claude/memory/` +
`graph_store`) is the fleet's only sanctioned memory face (unifying-strategy Grounding
2026-08-30: agents do not write to a side memory instead of `scribe capture`).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/*.toml`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` (the one launch path that composes a coding-CLI argv, so the only one this seam can prefix)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` + `cli/dispatch.py`

Corrected at review (2026-08-31): the draft also listed
`adapters/harness_bmadloop.py` as a launch path this story would touch. It is not — that
adapter launches `bmad-loop run`, not a coding CLI, so it carries no argv for a harness-seam
wrapper to prefix. The story leaves it untouched and `cli/spin.py` reports the layer's
inapplicability instead; see the dated SCOPE NOTE in the Change Log and the `deferred:`
entry for the bmad-loop engine.

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(wrapper injection, CCR byte-exactness, prefix byte-comparison, graceful-degradation
finding). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.2 and spec-marshal-token-economy CAP-2. The admission requirement
is live-zone-only compression (provider cache hot zone untouched) — headroom's documented
design; the test proves the property, not the vendor claim. Profile wrapper field follows the
harness-profile packaging convention (Story 1.10 / harness_profile.py precedent).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: added the Never against headroom's cross-agent SharedContext memory (second memory SoR risk; Scribe owns the memory face per the unifying-strategy Grounding)
- 2026-08-31: implemented. The seam is a profile-level `[wrapper]` table
  (`core/harness_profile.py`: `HarnessWrapper`/`parse_wrapper`, `WireWrap`/`resolve_wire_wrap`,
  `WIRE_LAYER_NAME`), applied by `adapters/harness_bmadbuild.py::dispatch` when Story 28.1's
  `[context]` `wire` layer resolves enabled; the packaged `claude` profile declares
  `headroom wrap claude --code-memory none --` with the CCR store pinned to
  `<loop home>/.marshal/wire` via `HEADROOM_WORKSPACE_DIR` (both key names verified against
  the installed headroom-ai 0.37.0: `paths.py::workspace_dir`,
  `cache/compression_store.py::_create_default_ccr_backend`, and — corrected at review — the
  `HEADROOM_MODE` read at `cli/wrap.py:658-661`, which forwards it as `--mode` when it starts
  the proxy; `cli/proxy.py`'s `--mode` option carries no `envvar=` binding, so citing that
  file as the evidence would send the next re-verifier to a dead end). Two of the spec's
  constraints are enforced STRUCTURALLY at parse time rather than by
  convention: a wrapper `argv` token carrying any launch placeholder is a
  `HarnessProfileError` (NFR-14 — the wrapper is a prefix, never a re-render), and
  `reversible` must be declared `true` (reversible-or-absent). Degradation is reported as
  `MRS-DISP-033` (WARN) on factory dispatch and `MRS-SPIN-017` (WARN) on `factory spin`.
- 2026-08-31: SCOPE NOTE — `marshal factory spin` cannot apply this seam. Marshal launches
  `bmad-loop run` there and bmad-loop, not marshal, launches the coding CLI, so there is no
  coding-CLI argv for a harness-seam wrapper to prefix. An enabled wire layer on that engine
  therefore reports what did NOT happen (`MRS-SPIN-017`, WARN, run proceeds unwrapped) rather
  than silently no-op'ing. Making it real there needs a loop-home-provisioned launcher shim
  plus a bmad-loop profile overlay pointing its `binary` at that shim (bmad-loop's own
  `adapters/profile.py` exposes `binary`/`env`, so it is reachable) — loop-home provisioning
  is Story 28.3's surface, not this seam's.
- 2026-08-31: TEST-SCOPE NOTE — the AC "prompt prefix byte-identical wrapped vs unwrapped" is
  proven in marshal's own terms (everything marshal composes after the prefix crosses
  byte-identically, asserted on encoded bytes) rather than against a live provider call; the
  live-zone-only property of the compression itself is the instrument's documented design, as
  the spec's own Design Notes anticipate ("the test proves the property, not the vendor
  claim"). Likewise the CCR byte-exactness AC is proven through an injectable stub wrapper
  that does a real compress → store → retrieve round-trip in the store marshal provisions:
  marshal declares no dependency on headroom (`pyforge-deps-test` would flag one) and the
  instrument's absence is precisely the case that must degrade, so no test here reaches for a
  real `headroom` binary.
- 2026-08-31: review pass — five code findings patched (see the Review Triage Log). Two of
  them tightened this seam's own structural guarantees: `wrapper.argv` must now name the
  profile's own `binary` (an overlay could otherwise retarget `binary` while keeping a
  packaged `wrap <tool> --` prefix and silently launch a different, never-authchecked CLI),
  and `reversible` is now load-bearing on the value actually used — `parse_wrapper` passes
  the parsed bool through instead of hardcoding `True`, and `resolve_wire_wrap` re-checks it
  and DEGRADES rather than raising, so a compression-layer misconfiguration can never fail a
  dispatch. The `.gitignore` rule was narrowed from the `.marshal/` namespace to
  `**/.marshal/wire/`: the namespace belongs to the Genesis seed subsystem, whose
  `seed-state.yml` has a documented "restore from version control" remedy, and whose
  `adopt.py` already solves its own dirty-tree problem with a `':!.marshal/'` pathspec
  instead of an ignore rule.

## Review Triage Log

### 2026-08-31 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 9: (high 0, medium 4, low 5)
- reject: 13: (high 0, medium 0, low 13)
- addressed_findings:
  - `[medium]` `[patch]` The new `.gitignore` rule blanket-ignored the `.marshal/` namespace,
    shadowing the Genesis seed subsystem's `seed-state.yml` (documented remedy: "restore from
    version control") and `plan.json`. Verified with `git check-ignore -v`. Narrowed to
    `**/.marshal/wire/` — `**/` retains the any-depth reach a loop home one directory deep
    needs, which a root-anchored `.marshal/wire/` would silently lose. New
    `tests/meta/test_wire_store_ignored_not_the_seed_namespace.py` asserts effective
    `git check-ignore` behaviour in both directions.
  - `[medium]` `[patch]` Nothing bound `wrapper.argv`'s wrapped-tool token to the profile's
    own `binary`, and `render_dispatch_argv` drops `binary_path` when wrapping — so an
    overlay setting `binary = "claude-dev"` under the packaged `wrap claude --` prefix would
    launch a different CLI than the one marshal probed and authchecked, with every existing
    test still passing. Now refused in `parse_profile` (the only place both values are
    known), joining the placeholder and reversibility refusals as the third structural rule.
  - `[low]` `[patch]` `reversible` was validated on the parse path then discarded —
    `parse_wrapper` hardcoded `reversible=True`, the dataclass field defaulted to `False`,
    and `resolve_wire_wrap` never read it, so a `HarnessWrapper` built any other way would
    apply silently-lossy compression. The parsed bool is now passed through and re-checked at
    the decision point, degrading with a named reason rather than raising (a raise inside
    `dispatch()` would turn a compression misconfiguration into a failed dispatch).
  - `[low]` `[patch]` `cli/dispatch.py` omitted `data["wire"]` on the `BuildHarnessError`
    path, contradicting `ports/build_harness.py`'s "a recorded fact of every dispatch" and
    diverging from spin's unconditional echo. The off-payload is now seeded as soon as the
    `[context]` payload it derives from exists, then overwritten by the real decision.
  - `[low]` `[patch]` The off/degraded payload dict was hand-spelled at three sites beside a
    `WireWrap.journal_payload()` that produces exactly it, so a new `WireWrap` field would
    drift them silently. All three now go through `journal_payload()`; the new tests derive
    the expected key set from that method rather than restating it.
  - `[low]` `[patch]` The Code Map listed `adapters/harness_bmadloop.py` as a launch path
    this story would touch; it is not touched, and cannot be — that adapter launches
    `bmad-loop run`, not a coding CLI. Corrected, with a pointer to the SCOPE NOTE and the
    matching `deferred:` entry.
  - `[low]` `[patch]` The implementation change-log entry cited `cli/proxy.py` as the
    evidence for the `HEADROOM_MODE` pin. Verified wrong: `proxy.py`'s `--mode` carries no
    `envvar=` binding; the real read is `cli/wrap.py:658-661`, which forwards it as `--mode`
    when starting the proxy. Citation corrected so the next re-verifier is not sent to a dead
    end.

## Auto Run Result

Status: done

### Summary of implemented change

Harness profiles gain an optional `[wrapper]` table that turns a launch into a wrapped launch
when Story 28.1's declared `[context]` `wire` layer resolves enabled. The decision is pure and
lives in one place (`core/harness_profile.py::resolve_wire_wrap`, three shapes: off /
degraded-with-a-reason / applied); the impure halves — probing the wrapper binary, creating the
loop-home-scoped CCR store, composing child env — live in the dispatch adapter. The packaged
`claude` profile declares `headroom wrap claude --code-memory none --` with the store pinned to
`<loop home>/.marshal/wire`. Three of the spec's constraints are enforced structurally at parse
time rather than by convention: no launch placeholder in a wrapper prefix (NFR-14), `reversible`
must be declared true, and `wrapper.argv` must name the profile's own `binary`.

### Files changed

- `src/.../core/harness_profile.py` — `HarnessWrapper`, `parse_wrapper`, `WireWrap`,
  `resolve_wire_wrap`, `WIRE_LAYER_NAME`, the extracted `_require_clean_relpath`, and the
  wrapper-aware `render_dispatch_argv`.
- `src/.../adapters/harness_bmadbuild.py` — wrapper-binary probing through the same
  `_resolve_binary` the profile uses, store-dir creation, child-env composition, PATH repair.
- `src/.../ports/build_harness.py` — `wrapper_binary_path` on `HarnessResolution`, `wire` on
  `DispatchLaunchResult`, `wire_layer` on the port method.
- `src/.../cli/dispatch.py` — passes only the `wire` entry to the seam; echoes and journals the
  decision on every envelope; raises `MRS-DISP-033` (WARN) on degradation.
- `src/.../cli/spin.py` — states the layer's disposition in JSON and text; raises
  `MRS-SPIN-017` (WARN) when an enabled layer cannot apply on the bmad-loop engine.
- `src/.../core/findings.py`, `core/verdict.py` — the two new codes, both `WARN`.
- `src/.../data/harness_profiles/claude.toml` — the one packaged wrapper.
- `.gitignore` — `**/.marshal/wire/` (the CCR store only, not the seed namespace).
- `tests/unit/{test_harness_profile,test_harness_bmadbuild,test_dispatch,test_spin,test_findings}.py`
  and `tests/meta/test_wire_store_ignored_not_the_seed_namespace.py` — station-owned coverage.

### Review findings breakdown

7 patches applied (2 medium, 5 low); 9 items deferred (4 medium, 5 low — carried in the
`deferred:` frontmatter list); 13 rejected as noise. No intent_gap, no bad_spec, no repair
loopback (`review_loop_iteration` stays 0).

### Follow-up review recommendation

`true`. Patched findings this pass: high 0, medium 2, low 5. Score = 3 × 2 + 1 × 5 = 11, which
is ≥ 5. No high-severity patch was applied; the recommendation rests on volume, not severity.

### Verification performed

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **6635 passed, 12 deselected**
  (6560 at baseline; +75 from this story). Re-run independently after the patch pass.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → **118 passed, 1 skipped**. Re-run
  independently after the patch pass.
- Mutation checks: reverting each guard individually fails exactly its own tests and nothing
  else (wire branch in `render_dispatch_argv` → 4; re-broadened `.gitignore` → 3; removed
  binary binding → 6; removed reversibility re-check → 2; removed pre-launch `wire` seed → 1;
  re-hand-spelled spin payload → 2). All restored and re-verified green.
- Vendor claims re-verified against the installed headroom-ai 0.37.0 rather than trusted:
  `paths.py::workspace_dir`, `cache/compression_store.py::_create_default_ccr_backend`,
  `cli/wrap.py:658-661` (`HEADROOM_MODE` → `--mode`), and `wrap claude --help`'s `--` passthrough
  and `--code-memory none`. Also verified `wrap`'s `--port` has NO `envvar=` binding, which is
  what makes the shared-proxy limitation a deferral rather than a patch.
- `git check-ignore -v` in both directions for the narrowed ignore rule; zero currently-tracked
  files newly ignored.

### Residual risks

The nine `deferred:` entries carry the full detail. The three that matter most:

1. **The bmad-loop engine is never wrapped.** AC 1 is satisfied on factory dispatch only.
   `factory spin` reports `MRS-SPIN-017` instead of silently no-op'ing, and the launcher-shim
   provisioning it needs is epics.md Story 28.3's surface. `factory dispatch --fleet` is the
   drain engine, so the wrapped engine is the one the fleet actually runs on.
2. **Concurrent wrapped dispatches share the first launcher's proxy and CCR store**, so the
   second session's store is not inside its own loop home and dies when the first worktree is
   torn down. Not scopable through the declarative wrapper surface (no `envvar=` on `--port`).
   Blast radius today is zero: the layer ships disabled.
3. **ACs 2 and 3 are proven at marshal's own boundary** — a real compress → store → retrieve
   round-trip through the directory marshal provisions, and a byte-comparison of the launch
   argv tail — not against a live provider call. Deliberate, and anticipated by the spec's own
   Design Notes ("the test proves the property, not the vendor claim").

Not this story's problem, recorded for the landing operator: the station-wide
`pyforge-marshal-test-coverage` gate fails pre-existing (98 modules, mostly `seed.*` /
`supervisor.*`; the two modules this story touches score 92% and 95%), and this change touches
files outside `recipes/`, so the PR needs the `maintenance` label. `pixi.toml` is untouched, so
no `environment.yaml` regeneration is required.
