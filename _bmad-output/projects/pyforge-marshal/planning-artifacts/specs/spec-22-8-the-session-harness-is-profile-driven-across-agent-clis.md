---
title: 'Story 22.8: The session harness is profile-driven across agent CLIs'
type: feature
created: '2026-08-27'
status: done
updated: '2026-08-27'
baseline_revision: 5bae7d330164a14de41ca789d8edefeab858a213
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
warnings:
  - "copilot profile: argv shape live-verified earlier on 2026-08-27 (COPILOT-OK, exit 0) but the same day's final smoke re-probe failed rc=1 'You have no quota' -- an account-quota condition no non-interactive probe can pre-detect; recorded in the profile's notes/authcheck_note."
  - "gemini model ids are hang-sensitive: the retired gemini-2.5-flash id made -p HANG past 180s (no error); the shipped map is probe-verified (gemini-3-flash-preview end-to-end; gemini-3-pro-preview accepted by the service but 429-quota-blocked on this account's free tier at probe time)."
  - "pre-existing suite red, untouched: tests/meta/test_skf_domain_skill.py::test_context_files_not_hand_edited fails on origin/main itself (CLAUDE.md carries a committed SKF block); fixing it requires editing CLAUDE.md, outside this story's permitted surface."
deferred:
  - "Wire the repo-defaults policy layer into the remaining compose() call sites (spin, gate, land, deploy, init, retire, adapters smoke, dispatch_verify) -- inert today because policy-defaults.toml carries only values equal to code defaults for the keys those paths read; recorded in Design Notes."
---

<intent-contract>

## Intent

**Problem:** `adapters/harness_bmadbuild.py` — the FR-52 seam for the second engine — is
hardcoded to ONE CLI: `_CURSOR_AGENT_BINARY = "cursor"`, `binary_present()` =
`shutil.which("cursor")`, and a fixed `["cursor", "agent", "--trust", "--workspace", …]`
argv. On 2026-08-27 all three real fleet-drain dispatches (atlas 17.1, mason, marshal)
died instantly with `Error: Authentication required. Please run 'cursor agent login'
first` (evidence: `implementation-artifacts/dispatch-runs/*/session.log` on each station)
— `binary_present()` was necessary-but-insufficient (binary on PATH, session dead on
auth), the skip was invisible to policy, and no other authenticated CLI on the machine
(claude was logged in the whole time) could be reached without editing marshal source.
bmad-loop already solved this class of problem with declarative CLI profiles
(`bmad_loop/adapters/profile.py` + packaged TOML), but marshal may not import it (AD-3).

**Approach:** Mirror the declarative-profile pattern in marshal-owned code. Ship packaged
TOML profiles (`src/pyforge/marshal/data/harness_profiles/*.toml`: `claude`, `cursor`,
`gemini`, `copilot`, `devin`) + a repo overlay dir (`_bmad-output/harness-profiles/*.toml`,
same-name overrides / new names extend), each declaring binary, detached-single-story argv
template (`{worktree}`/`{prompt}`/`{model_args}` placeholders), model-tier translation
(map / verbatim-passthrough / omit-with-finding), a cheap non-interactive authcheck argv +
success pattern (or a documented reason none exists), extra child env, and
repo-root-relative fallback bin dirs (the pixi-env binaries are not on a bare PATH). A new
STATIC policy key `harness_preference` (ordered tuple; code default
`claude, cursor, copilot, gemini, devin`) selects: resolution = first profile whose binary
resolves AND whose authcheck passes; every skipped candidate is a structured WARN finding
(`MRS-DISP-027`), and total failure is `MRS-DISP-003` naming everything tried. The SAME
preference drives bmad-loop: `render_policy_toml` derives `[adapter].name` from the first
preference entry with a bmad-loop counterpart (`core/harness_profile.py::
BMADLOOP_ADAPTER_BY_PROFILE`; no counterpart → template default + `MRS-POLICY-008` WARN on
the `--write-harness-policy` path). Wiring the machine's preference through
`_bmad-output/policy-defaults.toml` completes Story 1.10's documented-but-unwired
`repo_defaults` parameter of `core/policy.compose()` (new `PolicyLayer.REPO_DEFAULTS`),
read at the `marshal config` and `marshal factory dispatch` boundaries.

## Acceptance Criteria

Lifted from `epics.md` Story 22.8 (the epic's exact Given/When/Then):

- Given a station dispatch when the operator's policy expresses an ordered
  `harness_preference` then the session launches under the first profile whose binary
  resolves AND whose declared authcheck passes, every skipped candidate is a structured
  finding (never silent — the cursor-auth failure mode becomes a named skip), the launched
  argv is rendered from that profile's declarative template (worktree, prompt, per-CLI
  model-flag spelling and trust/permission flags), and the SAME one policy preference
  drives both engines — `marshal factory dispatch` directly, and bmad-loop via
  `render_policy_toml`'s `[adapter].name` derivation — with the previous cursor behavior
  preserved as the `cursor` profile.

Decomposed for traceability:

- `harness_preference` composes through the policy layers (code default →
  `_bmad-output/policy-defaults.toml` → project `marshal-policy.toml` → flags), is
  list-typed (not a `--set` target), validated as an ordered, duplicate-free tuple of
  profile-name-shaped strings, and appears in `marshal config`'s rendered output and
  `schemas/policy.json`.
- `compose()` honors its documented `repo_defaults` parameter (Story 1.10's promise):
  a value it supplies wins over the code default, loses to project/flags, and reports
  provenance `layer=repo_defaults`.
- Resolution is auth-aware: a profile whose binary exists but whose authcheck fails is
  skipped with a named finding — the exact 2026-08-27 failure shape can no longer launch.
- `MRS-DISP-003` (nothing dispatchable) names every candidate tried and why each was
  skipped.
- The cursor profile preserves the prior invocation semantics (trust flag + workspace +
  optional `--model` + positional prompt) with the model passed through verbatim, plus one
  empirically-driven addition: `-p/--print` — the CLI's documented non-interactive mode
  (full tool access), verified live 2026-08-27; the old no-`-p` TUI shape never once ran
  to completion headless (its only three launches died on auth first).
- Model tiers translate per profile: mapped names render via `{model_args}`; a profile
  with neither a mapping for the tier nor verbatim passthrough omits the model flags and
  reports `MRS-DISP-029` (WARN) — never launches a session with a guessed model name.
- `render_policy_toml` with the DEFAULT preference renders byte-identically to before
  (claude is both the first counterpart-bearing default entry and the template baseline);
  a preference led by a counterpart-bearing profile writes that `[adapter].name`; a
  preference with no counterpart keeps the template default, and the
  `--write-harness-policy` path reports `MRS-POLICY-008` (WARN).
- Detach semantics stay supervisor-compatible: every profile launches via the adapter's
  own `Popen(start_new_session=True)` so the child PID marshal journals and supervises is
  the session process itself — no profile uses a CLI's self-backgrounding flag (claude
  `--bg` would double-detach and orphan the tracked PID).
- All marshal tests use fake binaries (tmp scripts); no test invokes a real coding CLI.

## Boundaries & Constraints

**Always:**
- Binary invocation stays confined to `adapters/harness_bmadbuild.py` (FR-52 single seam;
  "THE ONLY module" docstring stays true — the module grows profile-plural rather than
  gaining siblings). Profile parsing/validation/argv-rendering/translation live in the
  pure `core/harness_profile.py` (AD-4: no `os`/`subprocess`/`time`/adapters imports).
- Mirror, never import: no `bmad_loop` import anywhere outside `harness_bmadloop.py`
  (AD-3 contract in `pyproject.toml` unchanged).
- Honest per-profile provenance: `verified` + `notes` in each packaged TOML state what was
  empirically smoke-tested (2026-08-27: claude, cursor, gemini, copilot on this machine)
  vs declared-untested (devin — no local binary exists; cloud service).
- `BMAD_ACTIVE_PROJECT` per-invocation + physical artifact paths; never
  `scripts/bmad-switch` (standing HARD rule).
- Ledger key: `22-8-the-session-harness-is-profile-driven-across-agent-clis`.

**Never:**
- No adapter-name `== "literal"` branching in `cli/`/`core/`/`ports/`/`supervisor/`
  (AD-19 guard); every per-CLI fact comes from profile data.
- Never launch on `binary_present`-alone evidence when the profile declares an authcheck.
- Never silently swallow a skipped candidate, an unloadable overlay profile, or an
  unmapped model tier.
- Never change the `done` ledger keys, the shipped CAP-1..7 behavior, or FR-184's clamp.

## I/O & Edge-Case Matrix

| Input / Scenario | Expected Behavior |
|---|---|
| Preference `claude, cursor, …`; claude binary + authcheck OK | claude profile launches; no skips |
| claude absent; cursor binary present but authcheck output lacks `Logged in as` | skip findings for both… cursor named as auth-failed (`MRS-DISP-027`); next candidate tried |
| No candidate resolves (or preference composes empty) | `MRS-DISP-003` ERROR naming every candidate + reason; no launch, no worktree side effects beyond preflight |
| Preference names an unknown profile | that entry skipped with a named finding; resolution continues |
| Overlay file `_bmad-output/harness-profiles/x.toml` malformed | `MRS-DISP-028` WARN naming the file; packaged set still loads |
| Overlay redefines a packaged name | overlay wins (same-name override), new names extend |
| Policy model tier `opus` on a map-bearing profile (gemini) | `{model_args}` renders the mapped spelling |
| Tier missing from a map-bearing profile / profile with no map and no passthrough (copilot) | model flags omitted + `MRS-DISP-029` WARN; session launches on the CLI's default model |
| `render_policy_toml` with default preference | byte-identical output to pre-story rendering |
| Preference `cursor, devin` (no bmad-loop counterpart) on `--write-harness-policy` | `[adapter].name` keeps template default; `MRS-POLICY-008` WARN |
| `policy-defaults.toml` supplies `harness_preference`; project layer silent | composed value wins over code default with `layer=repo_defaults` provenance |
| Malformed `harness_preference` (dup names, empty string, non-list) | that layer excluded with `MRS-POLICY-002`; previous layer's value stands |

## Design Notes (decisions recorded)

- **Overlay location:** `_bmad-output/harness-profiles/*.toml` (repo-level, tracked) —
  chosen over per-project config so one machine-wide CLI estate is declared once.
- **Detach decision:** Popen-detached `claude -p` (positional prompt) over `--bg`:
  marshal's dispatch supervisor tracks the exact child PID (`_spawn_dispatch_supervisor`
  arg 4; `gather_dispatch_journal_facts` reads it back), and a self-backgrounding CLI
  would make that PID a short-lived launcher.
- **cursor binary spelling:** `cursor-agent` (the standalone CLI actually verified
  2026-08-27; `cursor agent …` forwards to it — both report the same auth state). The
  invocation semantics (`--trust --workspace {worktree} [--model m] {prompt}`) are
  preserved with `-p` added for headless print mode (see the AC bullet above).
- **Trust flags per CLI (all empirically verified 2026-08-27):** claude
  `--permission-mode bypassPermissions`; cursor `--trust` (without it, `-p` stops at a
  trust prompt AND exits 0); gemini `--skip-trust` (same exit-0 refusal trap); copilot
  `--allow-all-tools` (required for non-interactive mode). Smoke probes must match on
  output, never exit code alone.
- **Authchecks:** claude `auth status` (`"loggedIn": true`), cursor `status`
  (`Logged in as`). gemini/copilot declare none — no cheap non-interactive auth probe
  exists in gemini 0.56.0 / copilot 1.0.80 (documented in each profile's
  `authcheck_note`); binary presence gates them and an auth failure surfaces in
  `session.log`.
- **repo-defaults wiring scope:** `compose()` + the `marshal config` and
  `factory dispatch` boundaries. Deferred (recorded, not silent): the remaining
  `compose()` call sites (`spin`, `gate`, `land`, `deploy`, `init`, `retire`,
  `adapters`, `dispatch_verify`) still compose without the repo layer — inert today
  because `policy-defaults.toml` carries only values equal to code defaults; wiring them
  is follow-up hygiene, not a behavior gap for this story's two engines.
- **bmad-loop translation source:** a code constant (`BMADLOOP_ADAPTER_BY_PROFILE`) in
  `core/harness_profile.py`, not a TOML field — keeps `render_policy_toml` free of
  file I/O and keeps the translation testable as pure data. Overlay profiles therefore
  have no bmad-loop counterpart by construction (falls through to the next preference
  entry).

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green (new: profile
  parsing/validation, resolution order, authcheck-fail skip + finding, per-profile argv
  rendering incl. model mapping and placeholder substitution, cursor
  behavior-preservation, repo-defaults layer composition + provenance, bmad-loop
  `[adapter].name` derivation + byte-identical default render; fakes only).
- `pixi run -e local-recipes chain-completeness-check` — no new findings vs the
  12-finding baseline (INV-B both directions).
- `pixi run -e local-recipes chain-layers-audit-check -- --project pyforge-marshal` —
  all checkpoints pass.
- One real-binary smoke run per verified profile (claude, cursor, gemini, copilot) from a
  throwaway dir: the profile's exact argv shape with a trivial print-and-exit prompt,
  short timeout, output-matched (never exit-code-only). devin: absent-binary skip path
  exercised with fakes only.

</intent-contract>

## Code Map

**Grows (the seam, kept single):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py`
  — profile loading orchestration, binary/authcheck probing, detached launch.

**New:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` —
  `HarnessProfile`, `parse_profile`, `load_profiles` (packaged + overlay),
  `render_dispatch_argv`, `translate_model`, `BMADLOOP_ADAPTER_BY_PROFILE` +
  `bmadloop_adapter_for_preference`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/{claude,cursor,gemini,copilot,devin}.toml`.

**Touched:**
- `ports/build_harness.py` (`HarnessResolution`/`HarnessCandidateSkip`; profile-aware
  `binary_present`; `dispatch(resolution=…)`; `DispatchLaunchResult.profile`).
- `cli/dispatch.py` (resolution after policy compose; MRS-DISP-003/027/028/029 wiring;
  journal + envelope carry the profile).
- `core/policy.py` (`harness_preference` STATIC key; `repo_defaults` fold +
  `PolicyLayer.REPO_DEFAULTS`).
- `cli/config.py` (`read_repo_policy_defaults`; field order/schema/unsettable;
  `MRS-POLICY-008` on `--write-harness-policy`).
- `adapters/harness_bmadloop.py` (`render_policy_toml` `[adapter].name` derivation).
- `core/findings.py` (register MRS-DISP-027/028/029, MRS-POLICY-008),
  `schemas/policy.json`, `pyproject.toml` (package the profile TOMLs),
  `_bmad-output/policy-defaults.toml` (this machine's expressed preference).

## Verification evidence (2026-08-27)

- `pixi run -e pyforge-marshal pyforge-marshal-test`: **6406 passed**, 12 deselected,
  1 failed — the failure is `test_skf_domain_skill.py::test_context_files_not_hand_edited`,
  red on `origin/main` itself before this story (CLAUDE.md carries a committed SKF block)
  and untouched here; the pre-change baseline showed the identical single failure at
  6322 passed. Net +84 tests, all green (profile parse/validation, packaged-set shape,
  overlay override/extend/malformed, resolution order, authcheck fail-on-exit and
  fail-on-pattern-despite-exit-0, fallback-bin-dir probing, argv rendering + literal
  substitution, model map/passthrough/omit, detach-session liveness, dispatch envelope
  profile + MRS-DISP-027/003 wiring, repo-defaults provenance/precedence/content-hash,
  `[adapter].name` derivation incl. byte-identical default render, MRS-POLICY-008).
- `pixi run -e local-recipes chain-completeness-check`: exit 2 with exactly the
  12-finding baseline, subjects byte-stable (INV-B holds both directions;
  `spec-marshal-single-story-dispatch` stays INV-A-clean with CAP-8 cited in-window).
- `pixi run -e local-recipes chain-layers-audit-check -- --project pyforge-marshal`:
  exit 0, all checkpoints pass (the `missing: retro` warn is the pre-existing baseline).
- Real-binary smoke (throwaway dir, exact profile argv via `load_packaged_profiles` +
  `render_dispatch_argv`, output-matched): **claude** rc 0 → `HARNESS-OK`
  (`--model haiku` verbatim); **cursor** rc 0 → `HARNESS-OK`
  (`-p --trust --workspace <dir>`); **gemini** rc 0 → `HARNESS-OK`
  (`-m gemini-3-flash-preview` via the tier map); **copilot** argv verified live earlier
  the same day (`COPILOT-OK`, exit 0), final re-probe quota-blocked (frontmatter warning);
  **devin** absent-binary skip path exercised with fakes.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5dfe5826c3` (2026-08-27, "feat(marshal): story 22.8 -- session harness profile-driven across agent CLIs (claude/cursor/gemini/copilot ve"). Ledger row `22-8-the-session-harness-is-profile-driven-across-agent-clis: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/policy-defaults.toml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-8-the-session-harness-is-profile-driven-across-agent-clis.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-marshal/pyproject.toml`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` (+18 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
