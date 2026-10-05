# AGENTS.md — cross-tool guide for this repo

The framework-neutral contract for every agent and harness (§ *How each harness loads this file*).

<!-- bmad:context -->
<!-- Verified 2026-09-29 against 060c54fba4. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## local-recipes (PyForge)

This is A (`rxm7706/local-recipes`), the PyForge control plane and BMAD Agentic-SDLC host: Dreams in `docs/dreams/`; Specs, spines, epics and ledgers under `_bmad-output/projects/<station>/planning-artifacts/`; a Django + Wagtail host at `src/platform/` and eight `pyforge-<station>` packages with their `django-<station>` portals under `src/shared/packages/`, on Python 3.14 via pixi (`pixi.toml` is the task and dependency registry). The conda-forge recipe factory (`recipes/`, driven by the `conda-forge-expert` skill) is one cell of A, not the product. B (`rxm7706/python-foundry`, private) is the lasting root, its engines rebuilt from Frame + Spec; A stays the control plane and the oracle, and the root of record until `pyforge.cutover_root` flips to `foundry`; A is never archived. That cutover is under contract (`spec-python-foundry-cutover`, Epic 44, `in-progress`: the Launch stories 44.3 / 44.7 / 44.12 / 44.13 landed; the file-move stories 44.4–44.6 are parked, `backlog` and never dispatched; 44.10 is retired and the other seven 44.x rows stay `blocked` until the operator flips them) — the estate has not moved.

## Policy

<!-- governance-currency:ignore-start (PIN.md and modes.md live on B -- rxm7706/python-foundry -- and are named here precisely to say they are NOT on A) -->
- Write each artifact on the root that owns it (the writer lock): foundry-product Dreams, Frames, Spec five-fields and kernel package commits are B's — never mint a second one here; A pins B's SHA (B's `docs/foundry/PIN.md`) and invents the factory, CFE and recipes until a foundry CFE exists.
- A capability crosses to B only by its mode — `rebuild` (B re-derives it; A is its oracle until it is `verified-in-foundry`), `retire` (never appears on B), `A-only` (with an expiry story or date) or `B-only` (named on a Spec before `done`); never `move`, never a package fold or copy of A into B. The table is B's `docs/foundry/modes.md`.
<!-- governance-currency:ignore-end -->
- Never mix `meta.yaml` and `recipe.yaml` recipes in one build run; the tooling rejects it.
- Never code from a bare prompt: a Dream in `docs/dreams/` and a Spec under `planning-artifacts/specs/spec-<slug>/` come first. Never author a new file under `docs/specs/` (legacy).
- Never hand-edit a `SPEC.md`; append to its `.memlog.md` with `uv run _bmad/scripts/memlog.py` and re-derive with `bmad-spec`.
- Never hand-edit `sprint-status-ledger.yaml` (generated); write the Tier-3 feed, then `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>` (the short key, `doctor`, not `pyforge-doctor`).
- Never track anything under `implementation-artifacts/`; it is Tier 3 and gitignored.
- Never run `scripts/bmad-switch` from a parallel agent; set `BMAD_ACTIVE_PROJECT=<slug>` and write physical `_bmad-output/projects/<slug>/` paths.
- Never run a bare `spec_surface_check.py --write-baseline`; stamp scoped with `--spec <project>/<spec>` after `git add`, from a clean tree.
- `src/platform/` never imports `pyforge.*`; reach station code through `pyforge.core.station_port`. No `services/` or `:800x` process tree.
- Any PR touching a path outside `recipes/` gets the `maintenance` label. A `pixi.toml` change regenerates `environment.yaml` in the same PR (`pixi project export conda-environment -e build > environment.yaml`); that check ignores the label.
- Never raise a `postgresql`/`libpq` pin to 18 or lift a psycopg/psycopg2/pgvector cap to clear a solve; the estate holds PostgreSQL 17 (fnd:CAP-12).
- Merge with `gh pr merge --merge`, never `--rebase` (squash is disabled in the repository settings; a rebase merge leaves no merge subject for landing evidence either). Create with `gh pr create --repo rxm7706/local-recipes`.
- Commit messages carry no `Co-Authored-By` line and no AI attribution; the `commit-msg` hook in `.pre-commit-config.yaml` refuses them (`steward setup` installs it; `precommit-config-check` reds the file going missing).
- Never open a feedstock, staged-recipes or upstream PR without an explicit ask; a green local build ends the task.
- Never flip a ledger `blocked` key, and never dispatch outward work (a new repo, an upstream PR, disabling CI) without operator confirmation.
<!-- governance-currency:ignore-start (the foundry target tree is not built on A; .claude/skills/pyforge-mason/ resolves only once mason Story 19.1 compiles it under the dated A-only exception below -- Mason's skill cell is then pyforge-mason plus conda-forge-expert, operator ruling 2026-09-28) -->
- New paths must fit the foundry target tree (`src/packages/`, `factory/`, `skills/{stations,personas,domain}/`, `docs/foundry/`); never mint a lasting `src/shared/packages/` path. One dated exception (operator ruling 2026-09-28; `docs/dreams/pyforge-mason.md` § Realization log, the 2026-09-27 entry *Mason has its own skills*): `.claude/skills/pyforge-mason/`, Mason's SKF-compiled station skill, is `A-only` until `pyforge.cutover_root` flips to `foundry`; B rebuilds Mason's skills under `skills/stations/`.
<!-- governance-currency:ignore-end -->

## Where things are

- Recipe lifecycle: `.claude/skills/conda-forge-expert/SKILL.md`. Invoke the skill before any conda work, including any edit under `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/` or `.claude/data/conda-forge-expert/`; where a story conflicts with the skill, the skill wins and the story records the deviation. Every conda-forge effort closes with a retro that edits that skill and its `CHANGELOG.md` with a semver bump — not deferrable; the effort is not done until it lands, and a retro with no findings still writes its CHANGELOG entry.
- Station code: read `.claude/skills/pyforge-<station>/SKILL.md` before touching `src/shared/packages/pyforge-<station>/`; use the CLI grammar, never `pyforge.<station>` internals.
- **Workspace-package conventions** (`src/shared/packages/pyforge-*/`): tests live in the package's own `tests/{unit,meta,conformance,integration}/` — never under `_bmad-output/projects/<slug>/tests/`, which holds only planning-scaffold mocks/fixtures. Where a package projects an exit-code verdict, that projection has a single-owner module (`verdict.py`) and, where the report contract is externally consumed, a shipped, frozen JSON Schema under `src/pyforge/<name>/data/report-schema.json` (`$id: urn:local-recipes:pyforge-<name>:report-schema`, additive changes only) — re-verified 2026-09-20: `pyforge-doctor`/`pyforge-warden` ship both; `pyforge-core`/`pyforge-marshal` ship `verdict.py` with no schema yet; the rest have neither. Not yet a universal requirement — the shape to follow where a package needs it.
- Cutover state — A/B roles, modes and the four campaign verbs (Launch the Foundry, Adopt Frames, Build the Intelligence Hub, Wire every BMAD-suite component), each marked done or not done: herald's dossier, `docsite/content/dossier.yml` § A→B. The contract is `spec-python-foundry-cutover` under `pyforge-steward`; the capability ledger is `docs/foundry/capability-ledger.yaml`.
- Architecture invariants and naming (station token, `python-<role>-<class>`, id prefixes, ledger keys): `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` under `pyforge-steward`; cite `canopy AD-n`, `pap:AD-n` for the host, and `fnd:AD-n` for the cutover ADs (folded into the steward spine 2026-09-08; the prefix remains the citation form).
- Library availability and pins: `docs/reference/library-llms-full.md` before importing or proposing a dependency.
- General documentation map: `docs/MAP.md` — Diátaxis-adapted index (`docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`).
- Governance: `docs/governance/`; Dream status vocabulary: `docs/dreams/README.md`; dates versus versions: § Dates below.
- The incident behind a rule in this file, and the reference material `CLAUDE.md` used to carry: `docs/reference/agent-instruction-notes.md` (§ *Read on trigger* below names when).
- pyforge-atlas subtree-exclusive rules (Kedro/Dagster/DuckDB internals — testing contract, AD-1 import boundaries, exit-code convention, code-grounded patterns): `src/shared/packages/pyforge-atlas/AGENTS.md`.
- bmad-suite member wiring (which of the 13 members is adopted, its wielding station, its provisioning path): `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` § 2 is the one durable home (AD-2) — routing detail lives in each wielding station's own `bmad-agent-<station>` persona skill, never restated here.
- The BMAD estate — installed core and modules, every skill by family, the suite roster with wielder and provisioning path, `bmad-*` pins, the marshal↔bmad-loop harness range, the release cadence: `docs/reference/bmad-estate-llms-full.md`, generated by `scribe catalog bmad-estate --write` and kept current by `bmad-estate-check`; never restate a version or a verdict from it here.

## Running and verifying

- The merge gate is `detectors-ci` measured as no new findings against `main`; it has been green at `main` since PR #1072 (2026-09-06), so a red run is yours.
- Planning edits keep `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`, `ledger-regression-check` and `story-status-check` green; epic stories and their ledger keys land in the same commit — **and so do epic headings and their `epic-<n>` keys.** Since 2026-09-14 `chain-completeness` INV-B compares `## Epic <n>` headings against `epic-<n>` ledger keys in *both* directions, so a heading with no key, or a key with no heading, is now a FAIL rather than an invisible gap. Two live orphans existed for weeks under the old check (steward Epic 18 was an `###`, marshal Epic 29 had no heading at all).
- Before any ledger write: `sprint-ledger-sync -- --project <station>`, then `story-status-check`; use `--repair-feed` only when deliberately reconciling a stale Tier-3 feed toward the tracked twin — a bare sync refuses when the feed would drop twin-only keys or overwrite `done`/`blocked` rows.
- To open a landing worktree, prefer `pyforge steward workspace start` / `status` / `clean` over hand-run `git worktree add` (see `spec-scratch-worktree-lifecycle`).
- Lint and types: `pixi run -e pyforge-guild lint-types` (ruff, `ruff format --check`, mypy over the ten `pyforge-*` packages, each from its own `[tool.ruff]` / `[tool.mypy]` on py314, mypy strict for `pyforge-core`; `target-version-check` reds a target drifting from the interpreter) — the same task `.github/workflows/lint-types.yml` and `pr-preflight`'s first leg run. The 2026-09-20 mypy baseline is disabled per module, per error code (`[[tool.mypy.overrides]]`), never `ignore_errors`; tighten the entry when you touch its module. `src/platform` keeps its own `platform-ci` lane (py312 target) and local twin `platform-ci-local -- --test`.
- BMAD skill renders need `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH"` in this shell.
- Pushes run `pr-preflight` through the `pre-push` hook (`.pre-commit-config.yaml`); `pyforge-station-tests` + `detectors-ci` alone miss the touched-module coverage floors (PR #1551 went red that way on 2026-09-20). `PYFORGE_PREFLIGHT_SKIP=1` is the one opt-out and is journaled to `.steward/preflight-skips.log`; `dispatch/*` branches are supervisor-gated and skip it, journaled.
- Only `pyforge-guild` exists at runtime: station code, the tasks it shells to, and docs name `-e pyforge-guild`, never `-e local-recipes` (the 10 GB recipe factory) — steward's `test_no_station_assumes_local_recipes.py` reds a station `src/` that does. On a laptop install `pyforge-foundry-full`, the SBOM and default laptop install (fnd:CAP-12): every station feature plus `build`/`grayskull`, on linux-64, osx-arm64 and win-64; add `pyforge-foundry-full-stack` for the platform's local stack (PostgreSQL 17, redis-server, object storage; linux-64). Its conda-recipe-manager resolves only to 0.5.0 and it has no feedrattler: run current crm/feedrattler with `-e grayskull`.
- Recipe-factory work is the one exception to the line above and runs in `-e local-recipes`; `-e pyforge-scribe` is only for `scribe graph compile` with its graphify / cocoindex / postgres extras. `pixi run -e pyforge-guild llms-full-check` exits non-zero when the library catalog drifts from `pixi.toml`.
- `bmad-estate-check` (repo scope, in `detectors-ci`) reds when `docs/reference/bmad-estate-llms-full.md` no longer matches its sources — reconcile with `pixi run -e pyforge-guild scribe catalog bmad-estate --write`, never by hand; `bmad-method-version-drift-check` (installed core vs the `pixi.toml` floor and upstream, warn-only) runs alone by name; `tea-test-review` (advisory, never a gate) is a `local-recipes` task.

## Known pitfalls

- Run `uv run` and every pixi task from the repo root; from a package directory `uv run` creates a stray `.venv` there (caught 2026-09-04).
- A merged story left at `backlog` in a ledger respawns on every drain; promote it with `sprint-ledger-sync` before landing.
- Unauthenticated GitHub probes fail open (`ok` at a 0/60 rate limit); check `gh api rate_limit` before trusting a green drift verdict.
- `--write-baseline` reads the working tree; a dirty checkout bakes uncommitted content into the baseline.
- Squash subjects break merge detection; `git merge-base --is-ancestor` is the proof a story landed.
- `.cmd` shims in `build.bat` need `call`, or the parent script exits.
- Marshal's `Deps:` parser is station-local; a cross-project gate is a ledger `blocked` row the operator flips.
- Never run `bmad-module-skill-forge uninstall`: its manifest lists every file under `.claude/skills/`, so it removes every skill dir, not the 16 skf ones (found 2026-09-06; the 6.12 shim retirement moved the exact skill-dir count, so don't restate a count here — `find .claude/skills -maxdepth 1 -mindepth 1 -type d | wc -l` gets the live one).
- A config pin in `_bmad/custom/config.toml` must sit at the installer's own key path (`[core] communication_language`, `[modules.bmm] user_skill_level`); the same key at a second path makes `render_skill.py` HALT with "ambiguous config value" and every rendering skill stops (caught 2026-09-06 after the 6.12 apply).
- `bmad-method install --action update -y` is not idempotent here: pass `--directory <repo>` (else a closed stdin exits 0 having written nothing) and `--modules core,bmm,skf` (else the cached custom module skf is deleted); re-apply local skill edits from the cached package diff (failure-modes.md traps 12-16).
- `bmad_loop`'s `DevPolicy.skill` (`[dev] skill = "bmad-dev-auto"`, the retired 6.x name, in the harness template and every loop-home `policy.toml`) is a permanent adapter discriminator, not the invoked skill name — never rename it or build a guard against its presence; `bmad_loop.policy` already refuses a bad value at render time (caught 2026-09-06: CAP-9's now-removed refuse-check assumed the opposite).
- Only `implementation-artifacts/` is the backlinked Tier-3 store shared across a project's worktrees. `planning-artifacts/` — including `sprint-status-ledger.yaml`, `epics.md`, `specs/` — is an ordinary per-worktree tracked file; never point a ledger/status write at another worktree's copy or the primary checkout. Caught twice independently (2026-09-06/07, parallel `bmad-build-auto` dispatches): an agent told its own implementation subagent the ledger was backlinked, and the subagent wrote the status flip into the shared primary checkout instead of its own worktree.
- `implementation-artifacts/` really is a symlink out of the worktree back to the primary checkout (verified: `readlink -f` resolves it there) — the Write/Edit tools refuse writes through it even from inside the correct worktree, since the target resolves outside the sandbox. This is a false positive for this one documented pattern, not a real problem: use Bash (`cat >`, a heredoc, `sed -i`) to write there instead, and expect an "Auto Mode Bypass" security flag on that step — it's expected here, not a sign anything went wrong (caught 2026-09-06/07, warden Story 11.1).

<!-- /bmad:context -->

## Behavioural guidelines (every harness)

1. **Think before coding** — state assumptions; for an ambiguous ask, present the interpretations,
   never pick one silently.
2. **Simplicity first** — the minimum change that solves the problem; nothing speculative.
3. **Surgical changes, healed tissue** — touch only what the task requires and match the
   surrounding style; but a broken window in what you touch (a lint or type error, a stale doc
   line, an obvious bug) is fixed now. "Pre-existing" says why a finding is not yours, never why it
   stays; defer only for a Dream-sized effort or a named blocker
   (`.claude/memory/feedback/pre-existing-findings-fix-now-is-the-default.md`).
4. **Goal-driven execution** — turn the task into verifiable goals and loop until they are verified
   locally; GitHub Actions is the arbiter, not the debugger.
5. **Dream to code, always** — every effort enters as a Dream seed in `docs/dreams/`, `bmad-spec`
   derives the Spec, a numbered Story precedes code (§ *Dream-first workflow* below). Gap-closure
   and small fixes are not exempt.
6. **State over action** — when a harness drives (`marshal factory dispatch` / `spin`, `bmad-loop`,
   `bmad-build-auto`), report progress by moving the story spec's frontmatter `status` through
   `draft → ready-for-dev → in-progress → in-review → done` (or `blocked`, with its blocking
   condition), not by narrating in chat.
7. **Harness-owned ledgers are read-only** — inside a harness run, never write the ledgers it
   writes (its Tier-3 `sprint-status.yaml` feed, the run's own state); change the story spec and
   let the harness reconcile. Outside a run, the write path is the one § Policy names: the Tier-3
   feed, then `sprint-ledger-sync`.
8. **Implementation and review stay separate** — implementation and adversarial review never run as
   one persona in one session: the reviewer reads the diff against the Spec, not the implementer's
   summary, and a failed review sends the story back with its failures recorded in the story spec.

## Team memory — read at session start, every harness

`.claude/memory/` is the checked-in **team** memory (owner: scribe; schema and promotion workflow in
`.claude/memory/README.md`). It is not any one operator's Claude Code auto-memory
(`~/.claude/projects/<encoded-path>/memory/`), which lives outside the repo and is invisible to every
other tool and person.

**The session-close ritual, in every harness, is `scribe capture` — stated once, here.** Capture
hygiene: no secrets, decision-grade facts only. See "Add to it" below for the command.

- **At session start** read `.claude/memory/MEMORY.md` — one line per entry: decisions, failure-mode
  traps, reference material. Claude Code gets it through `CLAUDE.md`'s `@.claude/memory/MEMORY.md`
  import; every other harness reads the file.
- **Add to it** with `pixi run -e pyforge-guild scribe capture --type <feedback|project|reference>
  --text "…"` at the moment a decision is made, or promote a personal auto-memory entry with
  `scribe capture --promote` (proposal, then confirmation). Never cite a home-directory file from a
  repo document — cite the promoted `.claude/memory/<type>/<slug>.md`.
- **Before a session ends,** anything only the operator can close (a credential-bound proof, a
  purge, a retire, a decision) is written with `scribe capture --type project` and, where a
  station owns it, as a `deferred-work-ledger.md` row — never left in chat or in one agent's
  auto-memory.
- **Entries every PR author hits:**
  `.claude/memory/feedback/a-pr-from-a-parallel-agent-that-adds-a-station-capability-mu.md`
  (a capability PR carries the whole chain),
  `.claude/memory/feedback/spec-surface-check-py-s-write-baseline-reads-git-ls-files-so.md`
  (`git add` before a scoped stamp),
  `.claude/memory/feedback/before-pushing-a-non-recipe-branch-replicate-every-ci-lane-t.md`
  (replicate every triggered lane locally; exit codes, never pipes),
  `.claude/memory/feedback/coverage-gates-run-per-station-in-that-station-s-own-pixi-en.md`
  (coverage floors per station, in that station's env),
  `.claude/memory/feedback/pre-existing-findings-fix-now-is-the-default.md`.

## How each harness loads this file

`AGENTS.md` is the one place the cross-tool contract is written; per-tool files carry only
tool-specific addenda, and `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`
reds a missing pointer or a duplicated section (`spec-pyforge-scribe` CAP-27; research:
`_bmad-output/projects/pyforge-scribe/planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md`).
Agentic frameworks (BMAD, Agno, CrewAI, LangGraph) start from the Dream in `docs/dreams/`.

| Harness | How it reaches `AGENTS.md` |
|---|---|
| Claude Code | `CLAUDE.md` imports it (`@AGENTS.md`) — the floor on every runtime. **≥ 2.1.277** (2026-09-18) also ships a built-in `agents-md` mod; its default mode `claude-md-or-agents-md` *stays out of any project that has a `CLAUDE.md`*, so this repo pins `instructionFiles: claude-md-and-agents-md` (operator user settings; marshal's dispatch launch passes it via `--settings`, Story 46.11) — then every `AGENTS.md` loads beside `CLAUDE.md`, deduped by path (the import never double-loads), and a nested `AGENTS.md` (e.g. `src/shared/packages/pyforge-atlas/AGENTS.md`) attaches on `Read`. Below 2.1.277 and on Bedrock / Vertex / Foundry only the import applies. Currency: `python scripts/claude_instruction_mode_check.py` (runtime, advisory). |
| Gemini CLI / Antigravity | `.gemini/settings.json` → `context.fileName: ["AGENTS.md", "GEMINI.md"]`; `GEMINI.md` is the Gemini-only addendum |
| Cursor | native (root and nested `AGENTS.md`); `.cursor/rules/*.mdc` add glob-scoped rules only |
| GitHub Copilot cloud agent / CLI | native (root + nested; nearest wins); `.github/copilot-instructions.md` is the Copilot-only addendum; `.github/workflows/copilot-setup-steps.yml` installs the Guild env |
| VS Code Copilot chat | `.vscode/settings.json` → `chat.useAgentsMdFile: true` |
| Devin | native (Knowledge also ingests `CLAUDE.md` and `.mdc` rules — which is why they must not duplicate this file) |
| Codex, Jules, Zed, Warp, Aider, goose, Windsurf, Amp, Factory | native (`AGENTS.md` open format; closest file wins) |

## Session guardrails (enforced, not asserted)

Twelve of this file's own rules — the guild-task/local-recipes mix-up, an ad hoc `pip`/`conda`/`npx`
install, a live `pixi add`/`pixi update`, `scripts/bmad-switch` from a worktree or with
`BMAD_ACTIVE_PROJECT` set, a `git commit` on `main`/the primary checkout or carrying
`Co-Authored-By`/AI attribution, `gh pr merge --squash`, a `gh pr create` missing `--repo
rxm7706/local-recipes`, `uv run` off the repo root, a bare `spec_surface_check.py
--write-baseline`, a direct write to `SPEC.md` / `sprint-status-ledger.yaml` / a tracked
`implementation-artifacts/` path, deleting every protected ref form and any `~/.bmad-loops/` loop home, and deleting a branch or tag whose tip would orphan commits — are additionally enforced by a repo-level `PreToolUse` hook,
`.claude/hooks/pre-shell.py`. It is registered on `Bash` and on `Edit`/`Write` in
`.claude/settings.json` (Claude Code) and on `beforeShellExecution` (deny) / `afterFileEdit`
(warn — Cursor has no before-edit deny) in `.cursor/hooks.json` (Cursor). **One script serves both
harnesses.**

The closed list of what it denies, and the one-line reason it gives for each — naming the
sanctioned form — lives in `docs/governance/guild-roster.json`'s `session_denials` array, the ONE
declared source; adding to it is a governance act, never a bare code change to the hook alone. The
script asserts its matchers are exactly that list at every run (a drift between the two is a loud
failure, not a silent gap) and never denies anything not on the list.

**Gemini CLI, GitHub Copilot CLI, and Devin have no verified deny surface for this hook.** For
them these twelve rules remain instruction-only, exactly as written elsewhere in this file — do not
assume they are enforced there.

The hook matchers are a command-line denylist only — git config such as `fetch.pruneTags=true` can
still prune protected tags without passing through Bash, so the server rulesets in
`docs/governance/rulesets/protected-refs.json` remain the guarantee; the hook is defence in depth.

## Trunk, worktrees, PRs (session path)

Trunk-based: branch from `origin/main`, live hours not weeks, merge back to
`main`. Every agent and subagent works in its own worktree and lands through
a PR. Prefer `pixi run -e pyforge-steward pyforge steward workspace start
<slug>` over hand `git worktree add` (`spec-scratch-worktree-lifecycle`).
The worktree branch is `<slug>`, not `main` — Git will refuse `checkout
main` there because the primary checkout already holds it.
Never commit on the shared checkout. Project addressing, `gh pr create` and the merge form are in
§ Policy. Cursor loads the same contract from `.cursor/rules/trunk-worktree-pr.mdc`.

## Scribe recall (session path)

When you need a **team decision**, an active Dream or SPEC, or a Herald fact
ledger number — not a guess from chat memory — run:

`pixi run -e pyforge-guild scribe recall "…" --mode planning`

Default recall omits `kind=code` graphify AST nodes. Use `--mode planning`
(docs/memlogs), `--mode memory`, or `--mode code` when you want one
surface — or `--kind` for an explicit bag. `--mode` and `--kind` are
exclusive. Scoped retrieve (`--scope <slug>`, including
Marshal planning-graph) also admits that slug's
`presentations/<slug>/facts.yaml`. Marshal `codegraph`
(`.codegraph/codegraph.db`) owns symbol navigation. Do not use `scribe recall --mode code` for symbols. Do not treat the
compiled graph as a substitute for this file or a station `SKILL.md`.

## Dream-first workflow (MANDATORY — every agent, every framework)
<!-- marshal-seed:begin region=dream-first-workflow model-version=1.0.0 sha=0f14025c -->
1. **No non-trivial work without a Dream + spec.** Before implementing a feature, migration,
   packaging effort, or refactor, a **Dream** must exist in `docs/dreams/<slug>.md`, and BMAD must
   have produced its **spec** (via `bmad-spec` or the planning chain) in
   `_bmad-output/projects/<slug>/planning-artifacts/`. Never code from a bare prompt.
2. **Keep the spec's status current** as work proceeds (`draft → ready → in-progress → shipped`) —
   no matter who does the work (Claude, Cursor, Gemini, Devin, Copilot, a human, or any agentic
   framework). BMAD specs track status in the framework; legacy `docs/specs/*.md` track it in
   `status:` frontmatter.
3. **Autonomy.** Marshal (`bmad-loop` / `bmad-build-auto`) can watch `docs/dreams/`, run `bmad-spec`
   on a new Dream, and drive the build unattended — so "a Dream is written" can trigger "BMAD
   creates the spec" with no human in the loop.
<!-- marshal-seed:end region=dream-first-workflow -->

1. **No non-trivial work without a Dream + Spec.** Before implementing a feature, migration,
   packaging effort, or refactor, a **Dream** (the raw, pre-technical aspiration) must exist in
   `docs/dreams/<slug>.md`, and **`bmad-spec`** must have distilled it into **the Spec** (five fields
   + companions) — the unit of contract everything downstream binds to. For product / platform scope
   the planning chain (`bmad-product-brief` → `bmad-prd` → `bmad-architecture` →
   `bmad-create-epics-and-stories`) then decomposes that Spec; it is not a substitute for it
   (Charter § The Lexicon §2). Spec and planning artifacts live in
   `_bmad-output/projects/<slug>/planning-artifacts/`; legacy `docs/specs/*.md` stay only for
   existing efforts and still carry the `status:` frontmatter that
   `python scripts/bmad_drift_check.py --specs` reads.
2. **Keep status current, whoever does the work** (Claude, Cursor, Gemini, Devin, Copilot, a human,
   any framework). A Spec moves `draft → ready → in-progress → shipped`; a story spec moves as
   § *Behavioural guidelines* item 6 says.
3. **Autonomy, and the measured front door.** Marshal (`bmad-loop` / `bmad-build-auto`) can watch
   `docs/dreams/`, run `bmad-spec` on a new Dream, and drive the build unattended — so "a Dream is
   written" can trigger "BMAD creates the spec" with no human in the loop. The default way to run
   a story is `marshal factory dispatch` (single story) or `marshal factory spin` (multi-story):
   both journal the run and benchmark it against the shared substrate/compression layers.
   Invoking `bmad-build-auto` bare is a sanctioned but unmeasured path — it forgoes those layers,
   the journal entry, and the per-harness savings benchmark that reads it.
4. **Gap-closure and realization work are not exempt.** Closing a realization gap, realizing a
   capability, or fixing an effort whose stories already exist still starts with a **Dream seed**
   (`status: dreamt`, an owning station, Kinships to every chain it binds) and `bmad-spec`
   deriving the Spec from it — never with "draft the story specs and dispatch". Operator ruling
   2026-09-12, minted on the CAP-17 run-state gap
   ([`docs/dreams/run-state-one-publisher.md`](docs/dreams/run-state-one-publisher.md)).
5. **Spec → Story before code.** A `ready` Spec is a contract, not a work order. Once `bmad-spec`
   produces it inside a BMAD project, decompose its capabilities into a numbered Story (or
   Stories) in that project's `epics.md` and reflect it in the ledger (the Tier-3 feed, then
   `sprint-ledger-sync`) — via
   `bmad-sprint-planning` / `bmad-create-epics-and-stories`, or by hand mirroring the project's
   own established numbering convention when those skills aren't invoked directly — **before**
   touching any file outside `docs/dreams/` or the Spec folder itself. A mechanically
   well-understood, single-CAP fix is not an exemption: skipping the Story skips the one place
   the dev/review loop and retro triggers this repo relies on actually fire.
6. **Address BMAD projects deliberately.** Before a BMAD skill that writes artifacts, know which
   project it targets (ask, or `scripts/bmad-switch --current`, and heed its desync warning). From
   a worktree or as a parallel agent, never switch: set `BMAD_ACTIVE_PROJECT=<slug>` and write
   physical `_bmad-output/projects/<slug>/` paths (§ Policy). On the primary checkout, switch only
   with `scripts/bmad-switch <slug>` — it re-points the two planning symlinks and the marker
   together; never hand-edit `_bmad/custom/.active-project`. After a BMAD write, check the file
   landed under the intended slug (`readlink -f`); a wrong target is silent, never an error.
   Config layers: `_bmad-output/PROJECTS.md`; the marker-and-symlink mechanism:
   `docs/reference/agent-instruction-notes.md` § *Multi-Project Pattern*.

## Portability contract (why this stays framework-neutral)
<!-- marshal-seed:begin region=portability-contract model-version=1.0.0 sha=9565ebc7 -->
BMAD *produces* the spec, but the spec stays portable — you are **not locked to BMAD**. The
neutral / framework-specific line runs *through* the spec:

- **Shared, portable layers:** the **Dream** (`docs/dreams/`, the WHY) and the **neutral
  Spec** (`bmad-spec`'s output — the WHAT + machine-checkable acceptance criteria, i.e. the
  verification oracle). Both are framework-agnostic by construction.
- **Per-framework layers:** decomposition (BMAD epics/stories vs. CrewAI crews vs. LangGraph
  nodes) and execution (orchestration, sprints, run traces) belong to whichever framework runs —
  BMAD, CrewAI, Agno, LangGraph, Devin, ….

So another framework has **two entry points**: (1) start from the **Dream** and do everything its
own way, or (2) consume the **neutral Spec** and diverge only at decomposition/execution —
which also lets you verify (and compare) any framework's build against the *same* oracle.

**The one property to protect:** the Spec's acceptance criteria must stay
framework-agnostic and machine-checkable (behavior + oracle — never "BMAD story 3.2 passed").
Keeping the Dream → spec handoff portable across agents is **Herald's** job.
<!-- marshal-seed:end region=portability-contract -->

BMAD *produces* the spec, but the spec stays portable — you are **not locked to BMAD**. The
neutral / framework-specific line runs *through* the spec:

- **Shared, portable layers:** the **Dream** (`docs/dreams/`, the WHY) and the **neutral
  Spec** (`bmad-spec`'s output — the WHAT + machine-checkable acceptance criteria, i.e. the
  verification oracle). Both are framework-agnostic by construction.
- **Per-framework layers:** decomposition (BMAD epics/stories vs. CrewAI crews vs. LangGraph
  nodes) and execution (orchestration, sprints, run traces) belong to whichever framework runs —
  BMAD, CrewAI, Agno, LangGraph, Devin, ….

So another framework has **two entry points**: (1) start from the **Dream** and do everything its
own way, or (2) consume the **neutral Spec** and diverge only at decomposition/execution —
which also lets you verify (and compare) any framework's build against the *same* oracle.

**The one property to protect:** the Spec's acceptance criteria must stay
framework-agnostic and machine-checkable (behavior + oracle — never "BMAD story 3.2 passed").
Keeping the Dream → spec handoff portable across agents is **Marshal's** job.

## The tiers (do not cross them)
<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=0b632764 -->
| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | The raw human aspiration / starting point (BMAD — *Build More Architect Dreams*); Herald renders it into a deck, and BMAD turns it into the spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | Former hand-authored spec tier — kept for existing efforts, **superseded by Tier 2**; author no new files here | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | The `bmad-spec` output + PRD, architecture, API/interface specs, epics+stories, gate reports — produced from the Dream. **The active spec lives here.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` (BMAD); your own tool dir for others | story files, sprint YAMLs, test outputs, retros | **local-only / gitignored** |

**Rules:**
- The **active spec is a BMAD artifact in Tier 2** — produced from a Tier-0 Dream. Don't hand-author
  a new spec in the legacy `docs/specs/` (Tier 1), and never drop one into a Tier-3 output dir.
- Each tool writes its working output into **its own** area (BMAD → `implementation-artifacts/`;
  Cursor → `.cursor/`; etc.) and **reads the spec from the BMAD planning folder** (Tier 2) — or a
  legacy `docs/specs/` file for an existing effort.
- `implementation-artifacts/` is gitignored/local-only — **nothing there should be git-tracked.**
<!-- marshal-seed:end region=tiers -->

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | The raw human aspiration / starting point (BMAD — *Build More Architect Dreams*); Herald renders it into a deck, and BMAD turns it into the spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | Former hand-authored spec tier — kept for existing efforts, **superseded by Tier 2**; author no new files here | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | The `bmad-spec` output + PRD, architecture, API/interface specs, epics+stories, gate reports — produced from the Dream. **The active spec lives here.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` (BMAD); your own tool dir for others | story files, sprint YAMLs, test outputs, retros | **local-only / gitignored** |

**Rules:**
- The **active spec is a BMAD artifact in Tier 2** — produced from a Tier-0 Dream. Don't hand-author
  a new spec in the legacy `docs/specs/` (Tier 1), and never drop one into a Tier-3 output dir.
- Each tool writes its working output into **its own** area (BMAD → `implementation-artifacts/`;
  Cursor → `.cursor/`; etc.) and **reads the spec from the BMAD planning folder** (Tier 2) — or a
  legacy `docs/specs/` file for an existing effort.
- `implementation-artifacts/` is gitignored/local-only — **nothing there should be git-tracked.**
- **Story specs are durable, not Tier 3.** A run drafts a story spec into its Tier-3
  `implementation-artifacts/`; once the story merges, promote that spec into the tracked
  `planning-artifacts/specs/` and commit it — it is the source of record.

## Pre-PR Pre-flight Checklist & Station Invariants

Before creating or pushing any PR touching `src/shared/packages/pyforge-<station>` or governance artifacts, agents **must** complete the following verification steps:

1. **Station Test Suite Verification**:
   Run the station unit, meta, and integration test suite:
   `pixi run -e pyforge-<station> pyforge-<station>-test`
2. **Detector & Merge Gate Audit — locally, before any push**:
   Run the full local twin of every lane that reds a PR:
   `pixi run -e pyforge-guild pr-preflight` — `detectors-ci` alone misses the `test-ci`
   spec-surface meta-test, the station suites and the touched-module coverage floors. Read
   every verdict from the exit code (`$?`, or write output to a file and read it back) — never
   through a pipe (`cmd | tail`, `cmd | grep`), which reports the pipe's status and false-greens
   (`docs/reference/judgement-vocabulary.md` § *Severity and exit codes*; the doctor sources use
   a different exit-code domain than the aggregator). Never push to `origin` to see what CI says:
   one push per batch of locally green fixes. `pr-preflight` does not cover container /
   `guild-container` (Docker/podman), atlas's Chromium/DuckDB/WASM gate (required under `CI=1`),
   herald's browser check or scribe's Postgres (`scribe-pg-up` first) — run those by hand when
   your diff touches them.
3. **Django Models & Migration Invariants**:
   When creating or modifying Django models in `src/shared/packages/pyforge-<station>/src/pyforge/<station>/dashboard/models.py`:
   - Generate the corresponding Django migration file (`000x_*.py`).
   - Run `test_dashboard_audit.py` to ensure `makemigrations --check` succeeds.
   - Update the `dashboard/__init__.py` split docstrings and pinned module assertions in `tests/meta/test_invariants.py`.
   - Add unit tests covering model creation, admin registrations (`admin.py`), and HTMX view handlers (`views_htmx.py`).
4. **Station CLI Duty Count Invariant**:
   When registering a new CLI duty in `cli.py`, update duty count assertions in `tests/unit/test_cli.py` and `tests/unit/test_restore_duty.py`.
5. **Spec Surface Reconcile, then a scoped stamp — never a stamp alone**:
   A governed file may only move with its owning Spec's `.memlog.md` naming the path (and the
   reason) — that entry is what `spec-surface` reads as the reconcile; a stamp without it
   launders drift, and a bare `--write-baseline` (no `--spec`) accepts every other Spec's
   pending drift as correct. Sequence, from a clean tree: (a) append the memlog entry to the
   owning Spec and every co-governor the detector names (`python _bmad/scripts/memlog.py
   append --workspace <spec-folder> --type event --text "Surface reconcile <date>: <path> …"`);
   (b) `git add` (the stamp reads `git ls-files`); (c) `python scripts/spec_surface_check.py
   --write-baseline --spec <project>/<spec>` for exactly those Specs; (d) re-run
   `pixi run -e pyforge-guild spec-surface-check` and read its exit code. A stamp is only valid
   until the next edit of any file in that Spec's surface — re-stamp after your last edit.
   Never re-stamp a Spec your change did not touch. A cross-package edit usually has a
   co-governor (`spec-pyforge-core` governs every station's `src/`): reconcile and stamp **every**
   Spec the detector names, one `--spec` each.
6. **One chain per station — a new capability is a Dream APPEND, not a new Dream**:
   - A station-owned feature (steward's, marshal's, …) enters as a dated entry on that station's
     Dream (`docs/dreams/pyforge-<station>.md`), then `bmad-spec` mints its `CAP-n` on the
     station Spec, then a numbered Story in the station's `epics.md` + ledger row, then a tracked
     story spec under `planning-artifacts/specs/` — before any file outside `docs/dreams/` or the
     Spec folder changes (§ *Dream-first workflow*; `docs/governance/spec-one-chain-per-station/`).
     "It exports into another station's tree" does not make a capability cross-station: the
     station that owns the code owns the chain.
   - A standalone `docs/dreams/<slug>.md` + `spec-<slug>/` pair needs a `fold-exemption:` from the
     **closed** list (`different-owner` · `different-lifecycle` · `cross-station-seam` ·
     `governance`); `cross-station-seam` is reserved for kernel / testing-kit seams every station
     imports (`spec-pyforge-core`, the testing kit), never a convenience for a feature that reads
     other stations' files. `chain-sprawl-check` reds an unexempted pair.
   - Qualify cross-project architecture citations using `canopy:AD-n` or `pap:AD-n`.
7. **Non-recipe PR mechanics** (the rules are in § Policy):
   - Any change outside `recipes/` → `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`.
   - `pixi.toml` or `pixi.lock` changed → run `pixi run -e pyforge-guild pyforge-station-tests`
     first: the shared-surface rule fires `pyforge-core` and all 8 station suites in CI, not just
     the station you touched.
   - A hand-landed story merges with `--subject "Merge <slug>/<key> into main"` so
     `landing_evidence` can read the key.
8. **Dream Registry & Doctor Hygiene Tests**:
   - When creating a new Tier-0 Dream in `docs/dreams/<slug>.md`, add its table row to `docs/dreams/README.md`.
   - Run `pixi run -e pyforge-doctor pyforge-doctor-test` to ensure `test_live_tree_dream_readme_missing_count` and `dreams-hygiene` pass.
9. **The `dashboard/` extra is the only place Django lives** (steward `tests/meta/test_invariants.py`,
   Story 9.1; atlas carries the same split):
   - No module outside `src/shared/packages/pyforge-<station>/src/pyforge/<station>/dashboard/`
     imports `django`, `channels` or `pyforge.<station>.dashboard` at module level — the base
     package must import and run its CLI without the `[dashboard]` extra installed.
   - The one sanctioned reach is a function-local `importlib.import_module("pyforge.<station>.dashboard.<module>")`
     that refuses (never falls back silently) when the extra is absent, and the meta-test pins it
     by name. `django.apps.apps.get_model` belongs to `src/platform/` migrations, not station code.
10. **Instruction files: one `AGENTS.md`, pointers elsewhere** (`spec-pyforge-scribe` CAP-27):
   - Cross-tool rules go in this file, outside the `bmad:context` block (that block is
     `bmad-project-context`'s — refresh it with the skill, never by hand). `GEMINI.md`,
     `.github/copilot-instructions.md` and `.cursor/rules/*.mdc` carry tool-specific addenda only;
     `scribe`'s parity meta-test reds a duplicated section, a missing `@AGENTS.md` import in
     `CLAUDE.md`, a missing Gemini / VS Code setting, or a memory path this file cites that does
     not exist.
   - `governance-currency` reds a skill, script or path named here that no longer resolves. It is a
     repo-scope detector, so `detectors-ci` and `pr-preflight` run it; `pixi run -e pyforge-guild
     governance-currency` runs it alone. Mark a deliberately historical name with
     `governance-currency:ignore-start/end`, never leave it bare.
   - An incident note leaves this file only after its text lands in
     `docs/reference/agent-instruction-notes.md`.

## Dates, tags and versions (one rule: is it a date or a version?)

Two formats that sort alike but can never be confused for one another. The distinction is
load-bearing — the Fleet console extracts dates with `\d{4}-\d{2}-\d{2}`, so a dotted
version string cannot be mistaken for a date, and vice versa.

| It is a… | Format | Where |
|---|---|---|
| **date** | `YYYY-MM-DD` — hyphenated ISO, zero-padded | filenames (`…-research-2026-07-25.md`), directory names (`prd-<chain>-2026-07-25/`), frontmatter (`created:`, `updated:`, `date:`), changelog date lines |
| **version** | `YYYY.MM.DD` CalVer, declared **unpadded** (`2026.7.30`) | `pyproject.toml`, package metadata, git tags |

**Dates are zero-padded** and therefore sort correctly as plain text — that property belongs
to the date format only, and several tools here rely on it.

**Versions are declared unpadded** because PEP 440 normalization strips leading zeros
whatever you write: `2026.07.30` becomes `2026.7.30` in the wheel filename, the metadata and
on PyPI. Declaring the normalized form keeps declared == displayed. The consequence is that a
normalized version does **not** text-sort correctly (`2026.10.1` sorts before `2026.7.9`), so
**never text-sort a version** — use `sort -V`, or `packaging.version.Version` as the key.
A second release on one day takes a fourth segment: `2026.7.30.1`.

**A git tag is a version alias, not a date** — unpadded, byte-identical to the version.
Do not pad it: 1,926 recipes here build their source URL from `{{ version }}` (57 as
`/v{{ version }}`), so a `v2026.07.30` tag against a `2026.7.30` version resolves to a URL
that 404s.

**Chain-scoped artifacts carry both** the chain and the date in the filename **and** declare
them in frontmatter (`chain:`, `created:`, `updated:`). Redundant on purpose: the filename is
greppable and sortable with no parsing, the frontmatter is authoritative, and a detector
cross-checks them — so a rename that forgets the frontmatter, or an edit that forgets the
rename, becomes visible instead of silently drifting.

## Keeping the BMAD planning docs accurate

The `_bmad-output/projects/pyforge-marshal/` artifacts are kept in sync with the live repo by a
detector + reconciler loop. After every CFE retro or skill MINOR bump, and whenever the detector
reports `surface-changed`, run `pixi run -e pyforge-guild bmad-drift-check` and follow
`_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md`. The detector also enforces the tier rules
above (it HARD-fails if a spec is git-tracked under `implementation-artifacts/`).

## Read on trigger

Each target below holds detail this file no longer carries; read it when its trigger fires.

| When | Read |
|---|---|
| Before changing or removing a rule in this file | `docs/reference/agent-instruction-notes.md` § *Moved from AGENTS.md* |
| Adding a script under `.claude/skills/conda-forge-expert/scripts/` (the three-place rule: script, CLI wrapper, pixi task + meta-test entry) | `docs/reference/agent-instruction-notes.md` § *conda-forge-expert v7.0.0 layout* |
| Running `detectors` or `fleet-picture` (their exit codes; paste `fleet-picture` stdout verbatim, never reformatted) | `docs/reference/agent-instruction-notes.md` § *Common Commands* |
| Scoping or planning a conda-forge story (`bmad-prd`, `bmad-create-epics-and-stories`, persona planning) | `docs/reference/agent-instruction-notes.md` § *BMAD ↔ conda-forge-expert integration* (Rule 3, planner constraints) |
| Choosing a skill for a request | `docs/reference/agent-instruction-notes.md` § *Skill Reference* |
| Working a legacy `docs/specs/*.md` effort | `docs/reference/agent-instruction-notes.md` § *Intake specs* |
| Decks and prototypes, or a session with the `claude-design` MCP server connected — round-trip by its tools, never ask for a manual export | `docs/how-to/presentation-deck.md` § *The MCP bridge* |
| BMAD method background before 6.12, or the full multi-project mechanics | `docs/reference/agent-instruction-notes.md` § *BMAD Method Documentation* |
| Before invoking a BMAD skill, provisioning or upgrading a bmad-suite member, or driving bmad-loop — which core, modules, skills and suite members are installed here, who wields each, the harness range, the cadence | `docs/reference/bmad-estate-llms-full.md` (generated; `bmad-estate-check` keeps it current — never restate a version or a verdict from it here) |

<!-- SKF:BEGIN updated:2026-08-26 -->
[SKF Skills]|7 skills|0 stack
|IMPORTANT: Prefer documented APIs over training data.
|When using a listed library, read its SKILL.md before writing code.
|
|[pyforge-atlas v0.1.0]|root: .claude/skills/pyforge-atlas/
|IMPORTANT: pyforge-atlas v0.1.0 — read SKILL.md before atlas pipeline work. Do NOT rely on training data. Use `pyforge atlas …` and POST /stations/atlas/mcp. Do not import pyforge.atlas internals. Do not replace conda-forge-expert. This is not cf-atlas-legacy.
|quick-start:{SKILL.md#quick-start}
|api: main(), run_pipeline(), read_dataset(), list_pipelines(), list_datasets()
|key-types:{SKILL.md#key-types} — PIPELINE_NAMES, AtlasMCPError
|gotchas: run from repo root; --version is first-token only; unknown MCP pipeline → AtlasMCPError
|
|[pyforge-doctor v0.1.0]|root: .claude/skills/pyforge-doctor/
|IMPORTANT: pyforge-doctor v0.1.0 — read SKILL.md before writing doctor diagnostics code. Do NOT rely on training data. Use pyforge doctor grammar, not pyforge.doctor imports. Findings stay advisory — not a second PR gate.
|quick-start:{SKILL.md#quick-start}
|api: main()
|key-types:{SKILL.md#key-types} — Finding (advisory signal), DoctorReport
|gotchas: run from repo root; pyforge doctor … not a freelance filesystem; monitor requires --fleet; warn never changes exit code; not a competing PR verdict
|
|[pyforge-herald v0.1.0]|root: .claude/skills/pyforge-herald/
|IMPORTANT: pyforge-herald v0.1.0 — read SKILL.md before writing herald/deck code. Do NOT rely on training data. Use the herald CLI, not pyforge.herald imports.
|quick-start:{SKILL.md#quick-start}
|api: main(), dispatch()
|key-types:{SKILL.md#key-types} — TOOL_NAME (herald), TOP_LEVEL_COMMANDS (deck|progress|success|notice|scheduler)
|gotchas: run from repo root; Path B grammar is pyforge herald …; POST /stations/herald/mcp only; Lane 1 CMS stays steward
|
|[pyforge-marshal v0.1.0]|root: .claude/skills/pyforge-marshal/
|IMPORTANT: pyforge-marshal v0.1.0 — read SKILL.md before writing marshal/loop-supervisor code. Do NOT rely on training data. Use the marshal CLI, not pyforge.marshal imports.
|quick-start:{SKILL.md#quick-start}
|api: main()
|key-types:{SKILL.md#key-types} — MarshalContext (--project front door), frozen exit domain
|gotchas: run from repo root; persona grammar is pyforge marshal …; do not import internals; Do not implement bmad-loop ingest in this skill
|
|[pyforge-scribe v0.1.0]|root: .claude/skills/pyforge-scribe/
|IMPORTANT: pyforge-scribe v0.1.0 — read SKILL.md before writing scribe/team-memory code. Do NOT rely on training data. Use the scribe CLI, not pyforge.scribe imports.
|quick-start:{SKILL.md#quick-start}
|api: capture_cmd(), graph_compile(), recall_cmd(), main()
|key-types:{SKILL.md#key-types} — CaptureType (feedback|project|reference), RecallAnswer (grounded miss is explicit)
|gotchas: run from repo root; --promote/--transcripts exclusive with --type/--text; recall never invents an uncited answer
|
|[pyforge-steward v0.1.0]|root: .claude/skills/pyforge-steward/
|IMPORTANT: pyforge-steward v0.1.0 — read SKILL.md before writing steward/platform code. Do NOT rely on training data. Use pyforge steward grammar (or the steward CLI), not pyforge.steward imports.
|quick-start:{SKILL.md#quick-start}
|api: build_parser(), resolve_duty(), main()
|key-types:{SKILL.md#key-types} — DutyResult is frozen evidence; duties never sys.exit (AD-8)
|gotchas: run from repo root; crash is exit 70 not 1; provision uses flags not nested verbs; do not replace conda-forge-expert
|
|[pyforge-warden v0.1.0]|root: .claude/skills/pyforge-warden/
|IMPORTANT: pyforge-warden v0.1.0 — read SKILL.md before warden work. Use `warden scan` / `pyforge warden scan`. Do NOT import pyforge.warden. Do NOT invent a second PR-gate verdict.
|quick-start:{SKILL.md#quick-start}
|api: main(), compose(), exit_code_for(), match_level_rung()
|key-types:{SKILL.md#key-types} — Status (seven-rung lattice), ComplianceReport
|gotchas: CLI is the sole gate; --doctor never exits 1; do not replace conda-forge-expert
<!-- SKF:END -->
