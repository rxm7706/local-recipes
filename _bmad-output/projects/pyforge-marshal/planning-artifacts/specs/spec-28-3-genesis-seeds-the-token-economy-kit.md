---
title: 'Genesis seeds the token-economy kit (Story 28.3, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'db6be12067e74e4bac79c294be28e1be89dcf0a9'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - caveman is ACTIVE in pixi since 2026-08-30 (2.4.0 patched build 2, linux-64 —
    `caveman-install` verified live; see recipes/caveman for the nodejs-24 hold);
    codegraph is likewise linux-64-only. Seeding must STILL treat each instrument as
    optional-with-named-finding (non-linux fleets, future regressions) — availability
    changed, the design constraint did not.
deferred:
  - summary: >-
      The codegraph AGENT INTEGRATION is not wired; only the index is provisioned.
    evidence: |-
      The Approach names "codegraph index build + agent integration"; AC 1's own check
      list names only "a present+fresh codegraph index", which is what shipped.
      `codegraph install --target claude --location local --yes` is the integration
      command and it writes the home's `.mcp.json` — a file marshal ALREADY owns and
      renders from the `mcp_servers` policy key (`cli/init.py::_render_mcp_json`,
      probed by `MRS-PREFLIGHT-012`). A second writer to that file would fight the
      renderer every provisioning cycle. Wiring it properly means teaching the
      `mcp_servers` render to append a codegraph entry when the `structure-graph`
      layer is enabled, which is Story 28.1's policy-render surface, not this seam's.
      `codegraph install --print-config <agent>` exists and writes nothing, so the
      merge is reachable when someone owns that render.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
    severity: medium
  - summary: >-
      A first codegraph index build blocks `marshal preflight` for as long as it takes
      (bounded at 900s), with no progress output and no background mode.
    evidence: |-
      `run_kit` calls `build_codegraph_index` synchronously; `codegraph init -y` on a
      large repo is genuinely slow, and provisioning runs unattended so the call is
      made quiet. A timeout degrades into a named WARN rather than a hang
      (`INDEX_TIMEOUT_S`), and the layer ships disabled, so blast radius today is
      zero — but an operator who enables `structure-graph` on a big station will see
      preflight appear to stall. A background/incremental build, or deferring the
      first build to `marshal seed kit --apply` only, would fix it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
    severity: medium
  - summary: >-
      Index freshness is a HEAD-timestamp comparison, so EVERY new commit marks the
      index stale — in a loop worktree that commits constantly, an enabled
      `structure-graph` layer sits in near-continuous `kit-item-stale` DRIFT.
    evidence: |-
      `detect/kit.py::_codegraph_check` compares the index mtime against `git log -1
      --format=%ct` and reports `stale` whenever `index_mtime < head_ts`. The dominant
      consequence is not the two accuracy bounds noted below but the CADENCE: a
      bmad-loop / dispatch worktree commits many times per story, and each commit
      moves HEAD's timestamp past the index's, so the layer re-reports DRIFT after
      essentially every commit until something re-syncs. `marshal preflight` does
      re-sync (and the successful-sync mtime stamp added in review keeps that from
      becoming PERMANENT drift), but nothing re-syncs between preflights — so a
      long-running story will show `kit-item-stale` on any `marshal seed check` taken
      mid-run. Secondary, and stated for completeness: uncommitted edits never mark
      the index stale, and a rebase that rewrites HEAD's timestamp forward marks it
      stale with no file change. The rule is deliberate — the same deterministic
      git-timestamp discipline SPEC-marshal-token-economy CAP-13 requires, no
      working-tree walk, and no possible false GREEN for the case that matters
      (commits landed, index not resynced). A cadence fix (a commit-count or
      time-window tolerance, or a post-commit hook that syncs) is a design choice this
      story deliberately did not make.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
    severity: low
  - summary: >-
      The deployed caveman skill is a snapshot; an upstream version bump is invisible
      to `marshal seed check`.
    evidence: |-
      The check verifies the file exists and carries the `token-economy-articulate`
      region — never that its upstream half still matches the installed
      `caveman-installer` payload. A `caveman` package upgrade therefore leaves every
      already-seeded home on the old skill body, reported OK. A body hash recorded
      alongside (the `state.managed[]` idiom `verbs/check.py` already uses for
      manifest artifacts) would close it; the kit deliberately keeps no state file of
      its own in this story.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
    severity: low
  - summary: >-
      AC 2 is proven structurally (the carve-out is deployed and verified), never
      behaviourally (that a session honours it).
    evidence: |-
      Nothing in a test suite can prove an LLM did not compress a verdict. What IS
      proven: the carve-out region names every surface in `ARTICULATE_SURFACES`, a
      deployment missing it is reported as incomplete rather than conformant, and
      marshal's own verdicts/journals are composed by marshal code that never passes
      through the skill at all. The residual risk is a dev session's own review
      verdict prose.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/kit.py
    severity: low
  - summary: >-
      Kit writes go through `ports.FsPort`, so `seed/fs.py`'s `never_write` guard does
      not cover them.
    evidence: |-
      Deliberate (see `seed/verbs/kit.py`'s module docstring): a kit item is not a
      manifest artifact and the relevant boundary is AD-11's loop home, which `FsPort`
      is the observable seam for — which is what lets `run_preflight` provision with
      its OWN injected port and stay visible to
      `tests/meta/test_ad11_write_boundary.py`. `_guarded_target` re-derives loop-home
      containment per write so the property is structural, but a manifest
      `never_write` glob that happened to match a kit path would not be honoured.
      Unreachable today: all three kit paths are module constants.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
    severity: low
  - summary: >-
      `run_preflight` still composes policy without the repo-defaults layer; only the
      `[context]` block was routed around it.
    evidence: |-
      The pre-existing asymmetry Story 28.2 deferred on `cli/spin.py` is the same one
      here. This story avoids inheriting it for the kit by resolving `[context]` from
      the HOME's own policy files (`seed_cli.resolve_context_layers`), so preflight
      and `marshal seed kit --repo-root <home>` agree — but the other 30 policy keys
      preflight reads still ignore `_bmad-output/policy-defaults.toml`. Fixing it
      properly changes resolution for all of them.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
    severity: low
  - summary: >-
      A hand-edited deployed caveman skill is clobbered with no `--force`, no backup,
      and no status that distinguishes "absent" from "present but edited".
    evidence: |-
      `_apply_caveman_skill` unconditionally writes the packaged upstream body plus the
      carve-out over whatever is at the target. `KitStatus.MISSING` conflates an absent
      file with one whose carve-out was removed, and the remedy row in
      `docs/finding-remedy-reference.md` tells the operator to run `--apply`, which
      overwrites. This departs from the package's own managed-artifact discipline for
      `copied-managed` artifacts, where `check` reports and `update` refuses without
      `--force`: the kit vocabulary has no `managed-file-modified` equivalent. Adding
      one means deciding whether a loop home's skill is operator-editable at all, which
      is a policy question this story did not settle.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
    severity: medium
  - summary: >-
      Kit provisioning takes no lock, so concurrent writers can race one loop home.
    evidence: |-
      `run_kit` acquires nothing, although `FsPort.acquire_advisory_lock` exists and is
      used elsewhere in this package. `marshal preflight` (during dispatch) and an
      operator's `marshal seed kit --apply` can run against the same home at once, as
      can two supervisors — `marshal factory spin` is already known not to serialize, so
      a second spin launches a concurrent supervisor. Two `codegraph init` runs against
      one `.codegraph/` or two writers on one `SKILL.md` is the failure. Unreached today
      because the layers ship disabled; the fix is an advisory lock on the home, whose
      scope (per-home vs per-item) is a design choice.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
    severity: medium
  - summary: >-
      Creating the CCR store directory is gated on an instrument that a bare `mkdir`
      does not need.
    evidence: |-
      `kit_checks` probes the instrument before the artifact for all three items, so
      with the `wire` layer on and `headroom` absent from PATH, `<home>/.marshal/wire`
      is never created and the check reports `instrument-unavailable` rather than any
      verdict about the directory. This is consistent with AC 3 read literally ("the
      layer is skipped"), and in tension with AC 1 ("verifies ... the CCR store dir").
      The module docstring's own justification for creating it eagerly — so a check
      before the first wrapped launch can tell "the store is provisioned" from "the
      wrapper silently fell back to a user-global cache" — describes precisely the case
      the gate prevents. Ungating just this item is a one-line change, but it makes the
      three items stop behaving uniformly, which is why it is a decision not a patch.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
    severity: medium
  - summary: >-
      The kit's ignore rules live only in this repository's `.gitignore`, so applying
      the kit to an external project dirties that project's worktree.
    evidence: |-
      This story added `**/.claude/skills/caveman/` and `**/.codegraph/` to THIS repo's
      `.gitignore` after a real apply left `?? .claude/` and `?? .codegraph/` in `git
      status` — which blocks `bmad-loop run`. `marshal seed kit --apply` against a loop
      home outside this repository reproduces the original problem there, with nothing
      to seed the equivalent rules. The fix is to write the two rules into the TARGET
      repo as a marshal-seed managed region, which means the kit starts owning a region
      in a file Genesis does not currently manage.
    location: .gitignore
    severity: low
  - summary: >-
      `resolve_context_layers` trusts the home's `.active-project` marker without
      confirming the project it names actually exists.
    evidence: |-
      If a home's marker is stale or names another project, the `[context]` block — and
      therefore which kit items get provisioned — is resolved from that other project's
      policy, silently. The repo's own convention treats the marker as unreliable shared
      state (CLAUDE.md's PARALLEL AGENTS rule exists because the marker and the
      artifact symlinks desync). Verifying the marker is backed by a real project policy
      file before trusting it is cheap; deciding what to do when it is not — fall back
      to all-off, or report a finding — is the open question.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
    severity: low
  - summary: >-
      Nothing reports when the `output` layer is on but the home's adapter is not
      `claude`.
    evidence: |-
      `CAVEMAN_SKILL_RELPATH` is a fixed `.claude/skills/caveman/SKILL.md` with no
      adapter awareness, while `run_preflight` resolves a per-home adapter and five
      harness profiles ship (`claude`, `copilot`, `cursor`, `devin`, `gemini`). The
      Claude-only path is backed by the canonical contract — `integration-layers.md`
      Layer 0 says "Claude Code skill deployed per loop home by Genesis" — so this is
      not a contract divergence, and the missing piece is only the report: a `copilot`
      home with `output` on gets a skill deployed where its agent will never look, and
      the check calls that conformant.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/kit.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Output compression (caveman skill) and the code-structure graph (codegraph
index) only help if they exist in every loop home — and today nothing provisions them, so
any adoption would be per-home ritual.

**Approach:** Genesis (`marshal seed`) installs the per-loop-home kit — caveman skill
deployment into the agent config, CCR store directory, codegraph index build + agent
integration — and `marshal seed check` verifies each piece, gated by Story 28.1's
`[context]` declaration. Dev sessions talk compressed; review verdicts, journals, and
escalation context stay fully articulated.

## Acceptance Criteria

- Given a seeded loop home with layers declared, when `marshal seed check` runs, then it
  verifies caveman-skill deployment, the CCR store dir, and a present+fresh codegraph index,
  each as a distinct check.
- Given a dev session in a seeded home, when a story lands, then the landed verdict and
  journal entries read as normal fully-articulated prose (never caveman-compressed).
- Given an unavailable instrument (pixi blocker, platform gap), when seed applies, then the
  seed still applies, the layer is skipped, and a named finding reports exactly which
  instrument and why.
- Given a home seeded with layers off, when checked, then no token-economy findings are
  raised (the kit is declared-off, not missing).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-3-genesis-seeds-the-token-economy-kit`.

**Block If:** A change would apply caveman compression to review verdicts / journals /
escalation context, or install the BSL-1.1 `@caveman-ai/cli` proxy.

**Never:** Hand-edits inside a loop home as the mechanism (Genesis owns provisioning).
Blocking a seed on a missing optional instrument.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/` (Genesis apply/check/derive)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py`
- loop-home provisioning path in `cli/init.py` / spin preflight

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(seed-check items, articulate-verdict guarantee, per-instrument named-finding degradation).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.3 and spec-marshal-token-economy CAP-3/CAP-4. Follow the Genesis
managed-region/manifest idiom (Epics 8–11): the kit is seed-managed state with a conformance
check, not ad-hoc files. The caveman recipe ships `caveman-install` (MIT installer); the
skill deploys into the agent's skills/plugins dirs per loop home.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-31: implemented. The kit is a closed three-item vocabulary in a new pure
  `seed/model/kit.py` leaf (`caveman-skill` ← layer `output`, `ccr-store` ← layer `wire`,
  `codegraph-index` ← layer `structure-graph`), read by a new read-only
  `seed/detect/kit.py` (`kit_checks` → three distinct `KitCheck`s; `kit_findings` → the
  non-conformant subset) and provisioned by a new `seed/verbs/kit.py` (`run_kit`, dry-run
  by default). `marshal seed check` gains one optional `context_layers` keyword and a
  `kit` section on `CheckReport`/its JSON; `marshal seed kit` is the seventh seed verb.
  `cli/init.py::run_preflight` calls the same verb with `apply=True` so the kit exists by
  provisioning rather than by per-home ritual, reporting degradation as the new
  `MRS-PREFLIGHT-015` (WARN, the same tier and reasoning as Story 28.2's `MRS-DISP-033`).
  Three new `FindingType` members (`kit-item-missing` / `kit-item-stale` DRIFT,
  `kit-instrument-unavailable` INFO) — **none HARD**, which is how "never blocks a run"
  is made structural rather than conventional.
- 2026-08-31: AC-2 MECHANISM NOTE — the deployed skill is the packaged upstream
  `SKILL.md` passed through byte-for-byte with a Genesis-managed
  `marshal-seed:begin/end region=token-economy-articulate` region APPENDED (the
  `regions/markers.py` idiom every hybrid manifest artifact already uses). The region's
  body is rendered from `ARTICULATE_SURFACES`, so the instruction the agent reads and the
  list the tests pin are the same data. A deployed skill WITHOUT that region is reported
  `missing`, not `ok` — "verdicts and journals stay articulate" is therefore a checkable
  property of the deployment, not a hope about the model.
- 2026-08-31: MECHANISM NOTE — Genesis deploys the skill's bytes itself rather than
  shelling out to `caveman-install`. Verified against the installed 2.4.0 rather than
  assumed: the installer's Claude Code mechanism is `claude plugin install` (user-global,
  marketplace, networked) plus `npx skills add`, and its `--config-dir` scopes hook files
  and `settings.json` only — its own `--help` says so. None of those can be scoped to one
  loop home. The payload is resolved from `caveman-install` on `PATH`
  (`<prefix>/lib/node_modules/caveman-installer/skills/caveman/SKILL.md`, the layout the
  recipe's own packaged tests assert), so the deployment tracks the installed package
  without hardcoding a prefix.
- 2026-08-31: VENDOR-CLAIM CORRECTION — the first index build is `codegraph init -y`, NOT
  `codegraph index`. `codegraph index --help` reads "Rebuild the full index from scratch
  (same result as a fresh init)", which looks interchangeable; run live against a
  directory with no `.codegraph/` it exits 1 with `Run "codegraph init" first`. Caught by
  an end-to-end smoke against the real instrument, not by reading the help text. `-y` is
  init's documented non-interactive flag and is load-bearing for unattended provisioning.
  Stale-index refresh uses `codegraph sync -q` ("for git hooks").
- 2026-08-31: `.gitignore` gains `**/.claude/skills/caveman/` and `**/.codegraph/`,
  alongside Story 28.2's `**/.marshal/wire/`. Verified live rather than predicted: a real
  `marshal seed kit --apply` in a scratch repo left `?? .claude/` and `?? .codegraph/` in
  `git status`, which would block `bmad-loop run` (it refuses a dirty worktree) and be
  swept up by the loop's own `git add -A`. Scoped to `.claude/skills/caveman/`, never
  `.claude/` or `.claude/skills/` — this repo TRACKS `.claude/skills/**`. `git ls-files |
  git check-ignore --stdin` confirms zero currently-tracked files are newly ignored.
- 2026-08-31: SCOPE NOTE — the codegraph AGENT INTEGRATION named in the Approach is not
  wired; AC 1's own check list names the index only, which is what shipped. The
  integration command writes the home's `.mcp.json`, which marshal already owns and
  renders from the `mcp_servers` policy key; a second writer there would fight the
  renderer. Carried as the first `deferred:` entry with the reachable path.

- 2026-08-31: review pass — 18 findings patched, no spec loopback (the intent-contract is
  unchanged). Two were high: (1) two tests resolved the real instruments from the ambient
  `PATH`, so they proved the machine rather than the code — green in a developer shell and
  red on CI/macOS, where none of the three instruments exists. `run_preflight` gained
  `kit_probe=`/`kit_index_builder=` DI seams alongside its existing `vcs`/`fs`/`harness`
  ones, and every kit test now DECIDES availability. (2) preflight provisioned the kit
  unconditionally after the halt-after-one-failure seed-file loop, so a home whose seeding
  had hard-failed could still spend up to `INDEX_TIMEOUT_S` on a real `codegraph init`;
  the block is now gated on the same `halted` flag and reports the skip. The rest, by
  theme: the post-apply verification now reads back through the SAME `FsPort` it wrote
  through (a raw-`Path` re-check reported its own successful applies as missing under any
  non-local port); `_result_findings` calls `kit_findings` instead of hand-rolling a second
  copy of the status→severity table; a failed step always yields a finding even when the
  re-check reads OK (a timed-out build leaves a partial db with a fresh mtime); a
  successful `codegraph sync` stamps the index mtime (sync-with-nothing-to-do otherwise
  left the layer in permanent DRIFT); the carve-out check compares the region BODY against
  `region_sha(articulate_region_body())` rather than accepting intact markers around an
  emptied body; preflight maps the kit finding's own severity through instead of flattening
  INFO to WARN; `build_codegraph_index` gained a `process=` seam so its argv/flags/ceilings
  are pinned by tests rather than by a docstring, and the `IndexBuilder` protocol now
  carries `stale` so create-vs-refresh is testable; `kit` is enrolled in the Story 12.5 CLI
  contract suite and in `test_p03_detect_is_pure`'s call list; `KitItem.is_dir`/`summary`
  are now read (presence is answered from data; the dry-run outcome explains the item);
  the timeout ceiling is surfaced in `seed kit --help`, its report, and the preflight
  envelope; `kit-item-stale`'s remedy is item-agnostic; and `marshal seed kit` is documented
  in `docs/adoption-guide.md` and the station SKILL.md (both added to `epic_surfaces`).

## Review Triage Log

### 2026-08-31 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 18: (high 2, medium 9, low 7)
- defer: 6 (recorded by the coordinator in `deferred:`; not implemented this pass)
- addressed_findings:
  - `[high]` `[patch]` **P1** — `test_preflight_provisions_a_declared_kit_item_through_the_injected_fs_port`
    and `test_run_check_surfaces_kit_drift_but_never_fails_on_it_unstrict` resolved real
    instruments from the ambient `PATH`. Reproduced: with
    `.pixi/envs/local-recipes/bin` stripped, `2 failed, 226 passed`. `run_preflight` gained
    `kit_probe=`/`kit_index_builder=`; every kit test now injects. Re-verified green on the
    full suite with a stripped `PATH`.
  - `[high]` `[patch]` **P2** — the kit block ran unconditionally after the
    halt-after-one-failure seed-file loop. Now gated on `halted`, with an INFO
    `MRS-PREFLIGHT-015` naming the skip; `test_preflight_skips_the_kit_when_seeding_halted`
    fails the builder if it is ever reached.
  - `[medium]` `[patch]` **P3** — preflight re-labelled every kit finding WARN, undoing
    `detect/kit.py`'s deliberate INFO for `kit-instrument-unavailable`. Mapped through a
    total `_PREFLIGHT_SEVERITY_FOR_KIT` table (a fourth `SeedSeverity` member fails loudly).
  - `[medium]` `[patch]` **P4** — `run_kit` wrote through an `FsPort` and verified with raw
    `Path`. `kit_checks` gained a `KitReads` seam (`FsPort` satisfies it structurally) and
    both passes now read the port. New `_PortOnlyFs` test proves the round-trip; the
    preflight test gained real `KitOutcome.action` and no-finding assertions.
  - `[medium]` `[patch]` **P5** — (a) a failed step now always yields a finding, reported as
    `kit-item-stale` when a partial artifact survived; (b) a successful sync stamps the
    index mtime, so a no-op resync cannot leave permanent DRIFT.
  - `[medium]` `[patch]` **P6** — the carve-out check compared markers only. Now compares
    the region body's `region_sha` against the current expected body; two new tests cover
    an emptied body and a hand-edited one.
  - `[medium]` `[patch]` **P7** — `_result_findings` hand-rolled a second status→severity
    table. It now calls `kit_findings` and amends via `dataclasses.replace`, paired with
    `zip(..., strict=True)`.
  - `[medium]` `[patch]` **P8** — `kit` added to `_SEED_VERBS` and `_MUTATING_VERBS`; the
    envelope-parity test now drives seven verbs; a new test routes
    `parse_args(["seed", "kit", ...])` through the real parser.
  - `[medium]` `[patch]` **P9** — `kit_checks`/`kit_findings` enrolled in
    `test_p03_detect_is_pure::test_detect_surface_never_writes`, with every layer on so all
    three branches run under the write blocker.
  - `[medium]` `[patch]` **P10** — added the emitted-`MRS-PREFLIGHT-015`-plus-`EXIT_OK`
    assertion both Story 28.2 sibling codes already carry, and an assertion that the kit
    section renders in the default `marshal seed check` text report.
  - `[medium]` `[patch]` **P11** — `build_codegraph_index` gained `process=`; four tests pin
    `init -y` vs `sync -q`, the positional, the two timeouts, the nonzero-exit reason and
    the never-raise contract. `IndexBuilder` is now a Protocol carrying `stale`, and the
    stale test asserts on what the builder was TOLD, not on a string derived elsewhere.
  - `[low]` `[patch]` **P12** — `KitItem.is_dir` is now read by `item_present` (presence for
    all three items answered from data) and `summary` by the dry-run outcome; the false
    docstring is corrected.
  - `[low]` `[patch]` **P13** — `kit-item-stale`'s remedy is item-agnostic in both `REMEDIES`
    and the reference doc.
  - `[low]` `[patch]` **P14** — `marshal seed kit` documented in `docs/adoption-guide.md`
    (new § 4) and the station SKILL.md; the drifted `seed.py:L846-L861` citation corrected
    to `L413`; both files added to `epic_surfaces["28"]`.
  - `[low]` `[patch]` **P15** — the verification arithmetic now reconciles and explains the
    function-count-vs-collected-count difference (parametrization).
  - `[low]` `[patch]` **P16** — `INDEX_TIMEOUT_S`/`SYNC_TIMEOUT_S` exported plus a derived
    `timeout_note()`, surfaced in `seed kit --help`, the kit report, and the preflight
    envelope (`data.token_economy_kit_note`).
  - `[low]` `[patch]` **P17** — `process=` threaded through `run_kit` (both `kit_checks`
    passes) and `verbs/check.py::run_check`.
  - `[low]` `[patch]` **P18** — deferred entry #3 re-framed around the CADENCE consequence
    (every commit marks the index stale) rather than only the two accuracy bounds.

## Auto Run Result

Status: done

### Summary of implemented change

Genesis now provisions and verifies the per-loop-home token-economy kit. Three items, each
gated by its own Story 28.1 `[context]` layer, each with a distinct check: the caveman
skill deployed into the home's Claude Code project skills directory with a
Genesis-managed articulate carve-out, the loop-home-scoped CCR store directory, and a
present-and-fresh codegraph index. `marshal seed kit` is the provisioning face (dry-run by
default, `--apply` executes) and `marshal preflight` calls it so a home is provisioned by
the lifecycle rather than by ritual. `marshal seed check` renders all three checks and
folds their findings into its graded report. Nothing in the kit can block anything: no kit
`FindingType` is HARD, the preflight code is WARN, and `marshal seed kit` returns 0 on
every completed run.

### Files changed

- `src/.../seed/model/kit.py` (new) — the closed `KitItemId`/`KitItem` vocabulary, the
  three relpaths, `ARTICULATE_SURFACES`, and `articulate_region_body()`.
- `src/.../seed/detect/kit.py` (new) — `KitStatus`/`KitCheck`/`InstrumentProbe`,
  `probe_instrument`, `resolve_caveman_skill_source`, `head_commit_timestamp`,
  `kit_checks`, `kit_findings`.
- `src/.../seed/verbs/kit.py` (new) — `run_kit`, `render_deployed_skill`,
  `build_codegraph_index`, `_guarded_target`.
- `src/.../seed/detect/findings.py` — three new `FindingType` members + remedies.
- `src/.../seed/verbs/check.py` — the optional `context_layers` keyword, `CheckReport.kit`.
- `src/.../cli/seed.py` — `resolve_context_layers` (the one new boundary read),
  `packaged_seed_model_version`, the `kit` verb, `--project` on `check`/`kit`.
- `src/.../cli/init.py` — preflight's provisioning step + `data["token_economy_kit"]`.
- `src/.../core/findings.py`, `core/verdict.py` — `MRS-PREFLIGHT-015` (WARN).
- `src/.../docs/finding-remedy-reference.md` — the three new rows.
- `.gitignore` — `**/.claude/skills/caveman/`, `**/.codegraph/`.
- `tests/unit/test_seed_kit.py` (new, 47 tests), `tests/meta/
  test_kit_artifacts_ignored_not_the_tracked_skills.py` (new), plus inventory/schema
  updates in `test_findings.py`, `test_init.py`, `test_seed_cli_seed_check.py`,
  `test_seed_detect_findings.py`, `test_seed_verbs_check.py`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — Epic
  28's `epic_surfaces` widened for this story's files.

### Review findings breakdown

Four review layers ran in parallel over the full diff since `baseline_revision` (tracked
changes plus the five new files rendered against `/dev/null`): blind-hunter, edge-case
hunter, verification-gap, and intent-alignment.

- **Patches applied: 18** — high 2, medium 9, low 7. Per-finding detail in the Review
  Triage Log above. The two high findings were both real defects a green suite was
  hiding: two tests decided their outcome from the developer's ambient `PATH` (red on CI
  and on macOS, reproduced as `2 failed, 226 passed`), and preflight provisioned the kit
  into a home whose seeding had already hard-failed, ignoring the halt.
- **Items deferred: 6** (appended to `deferred:`, which now holds 13) — the clobbering of
  a hand-edited deployed skill with no `--force`/backup/`managed-file-modified` status;
  the absent advisory lock around provisioning; `.marshal/wire` being gated on an
  instrument a bare `mkdir` does not need; kit ignore rules living only in this repo's
  `.gitignore`; `resolve_context_layers` trusting an unbacked `.active-project` marker;
  and nothing reporting when layer `output` is on but the home's adapter is not `claude`.
  Each is a design decision rather than a defect, which is why none was patched.
- **Items rejected: 5** — a clock-skew guard for a future-dated HEAD (speculative); the
  deferred-ledger twins from Stories 22.11/28.2 riding along in this diff (required by the
  intake detector, not this story's choice); `status: in-review` being outside the Spec
  lifecycle vocabulary (it is the story-spec workflow's own vocabulary, not the Spec's);
  and two restatements of findings already recorded as `deferred` entries 1 and 5
  (codegraph agent integration, and AC 2 being proven structurally rather than
  behaviourally).
- **No `intent_gap` and no `bad_spec`**, so no loopback ran and `review_loop_iteration`
  stays 0. The one candidate for `intent_gap` was the Approach naming "codegraph index
  build **+ agent integration**" while AC 1's check list names only the index. It resolves
  from the intent itself: `## Tasks & Acceptance` makes the Acceptance Criteria the
  acceptance surface, and those name three checks, none of them agent integration. The
  broader ambition is recorded as `deferred` entry 1 rather than treated as a gap.

### Follow-up review recommendation

`true`. Patched counts this pass: high 2, medium 9, low 7. A patched `high` alone sets the
flag; the score is also well over the threshold at `3 × 9 + 1 × 7 = 34` (≥ 5). Deferred and
rejected findings are excluded from both the count and the score.

### Verification performed

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **6754 passed, 12
  deselected**. The counts reconcile: **6720** at baseline (`db6be12067`), **+34** from
  this story's first pass (13 of which are `pytest.mark.parametrize` expansions of 2
  meta-test functions), **+21** from the review pass, and **0** removed → 6754. The
  story's own new test FUNCTIONS number 60 across two new files plus five extended ones;
  collected test COUNT and function count differ because of parametrization, which is
  what the earlier "6720 + 60 = 6733" gloss got wrong.
- Re-run with `.pixi/envs/local-recipes/bin` **removed from `PATH`** (no `caveman-install`,
  `codegraph` or `headroom` resolvable — the CI and macOS condition) → the same **6754
  passed, 12 deselected**. Before the review pass that same run was `2 failed, 226 passed`
  on the marshal-owned subset; no test now inherits instrument availability from the
  machine.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → **118 passed, 1 skipped**.
- END-TO-END against the REAL instruments in a scratch git repo (not stubs): `marshal seed
  kit --apply` deployed the real 6,518-byte upstream `SKILL.md` + the carve-out (7,418
  bytes, region parses), created `.marshal/wire/`, and — after the `init`-vs-`index`
  correction — built a real 159,744-byte `.codegraph/codegraph.db`. Re-run reported all
  three `already-present` with zero writes.
- Degradation proven live, not only by stub: the pre-correction run exited **0** with
  `[failed] codegraph-index: codegraph index -q ... exited 1: Run "codegraph init" first`
  and one DRIFT finding, while the other two items still applied — AC 3's exact sentence.
- `git check-ignore` in both directions, plus `git ls-files | git check-ignore --stdin`
  (zero currently-tracked files newly ignored).
- Repo detectors (`pixi run -e local-recipes detectors-ci`) re-run before and after. Net
  effect on marshal: `deferred-work` went from **failing to clean** for this station
  (`python scripts/deferred_work_intake.py --fix --project marshal` — scoped, never a bare
  `--fix`; it gave tracked twins to this story's 7 deferrals and, in the same pass, the 11
  already-un-twinned entries Stories 22.11 and 28.2 had left behind), and `spec-surface`
  lost two warns once `spec-marshal-token-economy/.memlog.md` named this story's paths.
  `chain-currency` still reports `pyforge-marshal: current`. Everything still red
  (`pyforge-steward/spec-pyforge-unifying-strategy`'s ~700-line surface drift,
  pyforge-atlas's un-twinned deferrals, `dream-chain`'s marshal-dependency-aware-dispatch
  gap, `bmad-drift`'s `sprint-change-proposal-2026-08-31.md` archive-hygiene fail) is
  pre-existing and foreign — verified as such rather than assumed, and deliberately left
  alone.

### Spec-surface state at close (re-checked after the commit)

The `--write-baseline` step this story flagged as owed turns out **not** to be owed for
`spec-marshal-token-economy`. Re-run from the clean, committed worktree
(`python -m pyforge.doctor.sources spec-surface`, the dispatcher entrypoint that owns the
verdict), that spec reports exactly four `drift-presumed: warn` lines, and all four name
paths **this story never touched** — `cli/dispatch.py`, `core/harness_profile.py`,
`core/policy.py`, `data/harness_profiles/claude.toml`, i.e. Story 28.2's. Not one of Story
28.3's 26 paths appears. The memlog reconciliation was therefore sufficient on its own, and
a stamp here would only absorb another story's un-reconciled drift — the precise hazard the
scoped-stamp convention exists to prevent. Left unstamped deliberately.

`pyforge-marshal/spec-pyforge-marshal` (the station umbrella spec) does list this story's
new files among its `drift: fail` lines. That spec was **already failing before this
commit**: its fail list is dominated by paths this story never touched (`test_spin.py`,
`test_vcs_git.py`, `harness_bmadloop.py`, `cli/config.py`, `dispatch_fleet.py`, and ~25
more), so its memlog is stale across many prior stories. Reconciling it is station-wide
maintenance, not this story's work, and stamping it from here would silently baseline all
of that foreign drift. Recorded rather than absorbed.

### Residual risks

The seven `deferred:` entries carry the detail. The three that matter most:

1. **codegraph agent integration is unwired** — the index exists, but nothing registers
   the codegraph MCP server in the home. It belongs in the `mcp_servers` render, which
   marshal already owns.
2. **A first index build blocks preflight** for up to `INDEX_TIMEOUT_S` (900s) with no
   progress output. Blast radius today is zero: the layer ships disabled.
3. **The deployed skill is a snapshot** — a caveman package upgrade leaves seeded homes on
   the old body, reported OK, because the check verifies presence + carve-out and records
   no body hash.

Not this story's problem, recorded for the landing operator: this change touches files
outside `recipes/`, so the PR needs the `maintenance` label. `pixi.toml` is untouched, so
no `environment.yaml` regeneration is required.
