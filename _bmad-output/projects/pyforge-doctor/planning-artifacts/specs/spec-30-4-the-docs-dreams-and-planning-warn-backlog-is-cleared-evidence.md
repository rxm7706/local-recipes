---
title: "30.4 review evidence: what each re-verified page and Dream edit rests on"
created: 2026-10-24
story: 30-4-the-docs-dreams-and-planning-warn-backlog-is-cleared
---

# Story 30.4 review evidence

The three worker records behind the story spec's AC2 and its Dream classes, kept verbatim. Each authored page's
`verified:` moved only after the review recorded here.

# Story 30.4 — docs/how-to review record (11 authored-stale pages)

Worktree: `exciting-faraday-1e4549-wt-preflight-warn-hygiene-2026-10-24`, branch `preflight-warn-hygiene-2026-10-24`.
Method per page: `git log --since=<verified>` and `git diff <rev-list -1 --before='<verified> 23:59'> HEAD` per stale
source (narrowed by grep for big files such as `pixi.toml`, `dispatch.py`, `worktree_sweep.py`), then every claim the
page makes that the source backs, checked against the current source or the installed binary's `--help`. `verified:`
moved to 2026-10-24 only after that check. Nothing committed.

Detector results after the edits (exit codes read directly):
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency` -> exit 0; none of the 11 pages
  in a warn line.
- `pixi run --frozen -e pyforge-guild governance-currency` -> exit 0 (`ok -- every skill, script and path named in 11
  governed document(s) resolves`); no finding names these pages.

---

## 1. docs/how-to/ai-engine-operations.md (verified 2026-09-20)

- `pixi.toml` -> envs the page names unchanged in shape: `python-agent-platform` (python 3.14.*), `platform-dev` (still
  composes postgresql 17 / pgvector / redis-server / silo), `dbgpt-sidecar` (still disjoint, linux-64 "container-only"),
  `pyforge-foundry-full-stack` (still composes `platform-dev`, now also `platform-object-storage`, linux-64). Pin bumps
  (silo, redis-server, hiredis, psycopg caps) and a new Liquibase activation env are not claims the page makes.
- `src/platform/Containerfile` -> comment-only change (shell-hook now also emits `LIQUIBASE_ANALYTICS_ENABLED=false`).
  `pixi install --frozen -e python-agent-platform` and the root build context still hold.
- `src/platform/compose/compose.yml` -> postgres image now `pgvector/pgvector:pg17`; `DJANGO_INSECURE_LOCAL_COOKIES`;
  **`LANGFLOW_SUPERUSER_PASSWORD` is now required** (`${...:?}`): `docker compose up` refuses without it.
- `docs/explanation/platform-deployment-architecture.md` -> Helm-side changes (flag overlays, pgvector image, upgrade
  notes, mcp-host sidecar, `LANGFLOW_SUPERUSER_PASSWORD` secret). Only the Langflow password matters to this page.
- Corrected: the compose step now says the stack refuses to start until `LANGFLOW_SUPERUSER_PASSWORD` is set (in the
  git-ignored `src/platform/compose/.env` or the shell) and why; the service list was incomplete (it named 4 of 8
  services) and now lists them all, with PostgreSQL 17 + pgvector. Added "(linux-64 only)" to the DB-GPT local env,
  which `pixi.toml` declares linux-64 only.

## 2. docs/how-to/configure-your-coding-agent.md (verified 2026-09-20)

- `AGENTS.md` -> harness table, the 2.1.277 / `claude-md-and-agents-md` pin, the numbered pre-PR checklist and the
  team-memory boot read are all still as the page states (changes were the repo summary, guardrails, preflight scope,
  session-close ritual, and so on).
- `CLAUDE.md` -> sections moved to `docs/reference/agent-instruction-notes.md`; the bare `@AGENTS.md` import and the
  Claude-only addenda remain. No change the page relies on.
- `harness_profiles/claude.toml` -> launch adds `--session-id`; new `resume_argv` / `fix_only_argv` and `[model_list]`.
  Every argv still passes the same `--settings` agents-md pin, so "dispatched sessions are pinned for you" holds.
- `test_instruction_surface_parity.py` -> two new tests (session-close ritual named once; each harness file points at
  it). The page's "keeps the pointers, the settings and the harness table honest" still holds.
- Also checked (not stale): `.gemini/settings.json`, `.vscode/settings.json` (`chat.useAgentsMdFile: true`),
  `scripts/claude_instruction_mode_check.py` exit codes, `claude-instruction-mode-check` in guild-tasks.
- No correction needed.

## 3. docs/how-to/launch-a-cost-saving-interactive-session.md (verified 2026-09-24)

- `CLAUDE.md` -> the Interactive session path commands (`caveman-install --only claude --with-hooks`,
  `headroom wrap claude --code-memory none`) are unchanged. No change the page relies on.
- `pixi.toml` -> `caveman-installer` moved from the SelfExplainML 2.7.0 build to conda-forge `>=4.0.0` (still in the
  pyforge-guild linux-64 target table); `headroom-ai` floors unchanged for the guild feature; `sqlite-vec` floor bump.
  Checked the installed binaries: caveman-install 4.0.0 `--help` (`--only`, `--with-hooks`, `--force` exist; Claude
  hooks are now SessionStart/SubagentStart/UserPromptSubmit/SessionEnd plus a mode statusline); headroom 0.37.0
  `wrap claude --help` (`--code-memory none`, `--memory`, `--1m`, `-- -p` all as stated).
- `docs/dreams/pyforge-marshal.md` -> 2026-09-29 entry confirms dispatch applies `wire` (headroom) and `output`
  (caveman) on every dispatch; the codegraph layer is new but not this page's subject. No change the page relies on.
- Corrected: the hook list (four hooks, mode badge) and `--force`; noted `caveman-install` is in pyforge-guild on
  linux-64 only; replaced the non-existent terminal command `caveman stats` (caveman-installer 4.0 ships only the
  `caveman-install` binary) with the in-session `/caveman-stats` skill, and said the report leaves savings unknown.

## 4. docs/how-to/manage-worktrees-with-bmad.md (verified 2026-09-19) — 1 dead reference

- `steward/workspace.py` -> Stories 68.1, 69.1, 13.6 and review rounds: the sweep keeps what it cannot decide; a clean
  worktree git proves landed gets a `.landed.txt` note instead of a tarball; a workspace started `--from` another
  branch is landed once its branch is on main. `start <slug>` still creates branch `<slug>` off `origin/main`;
  `ls`/`status`/`clean`/`clean --delete` as stated.
- `marshal/cli/dispatch.py` -> many stories (liveness, stale runs, landing reuse, ruff, recall). The page's claims
  (worktree from `origin/main`, one detached `bmad-build-auto` session, `BMAD_ACTIVE_PROJECT` per invocation, journal,
  `marshal land`) still hold.
- `scripts/worktree_sweep.py` -> +1151 lines since 09-19 (remote sweep, `--retire`, preserve tags, STALE-LOCK,
  ORPHAN-DIR, patch-equivalent reporting). The page had already been rewritten for these; verified each verdict,
  flag, the remote KEEP/DELETE/INSPECT rules, the `sweep-<sha8>` preserve tag, the code floor and the ruleset refusal
  against the current script. No claim wrong.
- `scripts/bmad-switch` -> re-exec under `pixi run -e pyforge-guild` when the scope primitive cannot load. The
  marker + two symlinks and `BMAD_ACTIVE_PROJECT` precedence still hold. No change the page relies on.
- Dead reference fixed: `.claude/worktrees` (resolves only where a worktree has been made; ignored only through the
  primary checkout's `.git/info/exclude`, so dead in a fresh clone or worktree). Rewritten as the placeholder paths
  `.claude/worktrees/<name>/` etc., with "which exist only once an agent has made a worktree there".
- Corrected: `steward workspace clean` now notes that a clean, provably landed worktree gets a `.landed.txt` note,
  not a tarball (Story 69.1).

## 5. docs/how-to/monitor-the-fleet.md (verified 2026-09-20)

- `scripts/fleet_picture.py` -> new ATTENTION probes (Pages deploy staleness 48.2, CI pause drift 45.1, stale
  dispatch runs 92.1, stranded dispatch work, superseded refused landings). Still read-only, always exit 0, still
  reads `marshal status --format json`. Its columns are done / cmpl (completeness) / proj (projection) / blkd per
  station and per epic plus a state column — the page said "in-progress", which the report has no column for.
- `scripts/fleet-poll-hourly.sh` -> sync moved to `scripts/fleet_poll_sync.sh` (Story 87.13): fetch every checkout;
  only a `loop/*` branch is fast-forwarded to `origin/main` (diverged is reported), only that branch is pushed;
  never rebases, never pushes `main`. The page said it rebased every checkout and pushed their branches.
- `marshal/cli/main.py` -> `chain` verb removed, `preserve` added, FlagOff / repo-root error handling. `status`,
  `status --project`, `watch --fleet` unchanged. No change the page relies on.
- `steward/sprint_ledger_query.py` and `.claude/skills/bmad-sprint-ledger-query/SKILL.md` -> flags moved to the
  flagd tree keys. `--unimplemented/--ready/--running`, the `next` values and the one `marshal watch --fleet
  --format json` read are unchanged; the page names no flag. No change the page relies on.
- `pixi.toml` -> `fleet-picture`, `sprint-ledger-query`, `loop-stall-check`, `baseline-drift-check` tasks still in
  guild-tasks. No change the page relies on.
- Corrected: the report's counts (completeness, per-epic, state column), ATTENTION examples marked as examples with
  the new stale-run and Pages items, and the poll tick's git behaviour.

## 6. docs/how-to/pause-ci.md (verified 2026-10-15)

- `docs/governance/ci-surfaces.yaml` -> 2026-10-15/16 resumes (rows back to `live`, pause metadata dropped). The page
  states no live inventory; field names, states and the six grandfathered names unchanged. No change the page relies on.
- `steward/ci.py` -> Story 108.1: a `retired` row (and, as before, a `value` or `paused-manually` row) is never counted
  as paused by the master switch, even when its workflow reads `PAUSE_ALL_CI`.
- Corrected: added one sentence on that exception to the master-switch paragraph.

## 7. docs/how-to/reconcile-spec-surface.md (verified 2026-09-20)

- `doctor/sources/chain.py` -> large changes (unevaluable surfaces, comment/quote parsing, co-governors). The finding
  text and severities the page quotes (`drift` fail with "reconcile the spec, then --write-baseline --spec",
  `drift-presumed` warn) are unchanged; Doctor exit domain (fail -> 2) unchanged.
- `scripts/spec_surface_check.py` -> Story 82.3: a scoped stamp now refuses (exit 1, baseline untouched) when a
  differing path is neither named in a moved memlog nor passed with the new repeatable `--accept PATH`; refusals for a
  corrupt baseline or an unevaluable surface; `git ls-files -z`.
- `scripts/.spec-surface-baseline.json` -> stamps only. No change the page relies on.
- `_bmad/scripts/memlog.py` -> Windows UTF-8 stdout only; the no-frontmatter refusal still holds. No change the page
  relies on.
- Corrected: Step 4 now explains the scoped-stamp refusal and `--accept PATH`, preferring a fixed memlog entry.

## 8. docs/how-to/refresh-the-estate.md (verified 2026-10-13; page last edited 2026-10-13 19:17, so diffed from there)

- `steward/estate_reconcile.py` -> 100.7: checks run in the Guild env through `pixi run --as-is -e pyforge-guild`
  (the env must already be installed); 108.1: env-matrix generator fixed and `pixi-env-matrix-check` added; a failed
  generator now reds the run (exit 1) after the remaining generators, checks and stamps run, naming it first; only
  `generate-bmad-suite` still stops early; BMAD-estate catalog runs in the Guild env; warn-only checks added. The
  generator order the page lists is unchanged.
- `steward/estate_verify.py` -> `--lane` now also runs the lanes it depends on, dependencies first (herald 45.1);
  lanes with no env run in pyforge-guild; register probes for an env this run did not install read `skipped`;
  red rows carry an `output_tail`; the Guild size bound measures the env only. Flags (`--env`, `--lane`, `--probe`,
  `--all`, `--keep`, `--ignore-ci-pauses`, `--budget-minutes`) and the default tier still as stated.
- Corrected: added the Guild-env prerequisite and failed-generator behaviour to `reconcile`, and the `--lane`
  dependency, `skipped` probe and journal output-tail behaviour to `verify`.

## 9. docs/how-to/run-and-understand-detectors.md (verified 2026-09-20)

- `scripts/detectors.py` -> new `--jobs N|auto`; `detectors-ci` now runs `--scope repo --jobs auto`;
  `scripts/ci_surface_gates.py` is scanned as a detector; a detector's task must now run the script by its
  repo-relative path (doctor 49.1), not merely mention the file name; doctor sources fold-complete,
  bmad-output-hygiene, dreams-hygiene, frontmatter-duplicate-keys threaded in.
- `pixi.toml` -> `detectors-ci` cmd now `python scripts/detectors.py --scope repo --jobs auto`.
- `doctor/sources/__init__.py` -> new sources (ci-pause-drift, pages-liveness, fold-complete,
  frontmatter-duplicate-keys) and the `degrade_on_exception` call-site list; nothing the page states changed.
- Also found while checking: docs-currency has a fourth check, `generated-stale` (doctor 30.3, 2026-09-24), which the
  page's "Three checks" left out.
- Corrected: `detectors-ci` flags and a `--jobs` line; the registry-gap scan list and the "task must run the script by
  path" rule; docs-currency now lists four checks with a `generated-stale` fix line.

## 10. docs/how-to/station-cli-operations.md (verified 2026-09-20)

- `pyforge-core/dispatch.py` -> `pyforge --help` now names the stations not installed with their env; a roster
  station not installed exits with the `pixi run -e pyforge-<station>` command; `context` is a bare-noun alias for
  `marshal context`.
- `steward/cli.py`, `steward/tests/unit/test_cli.py` -> new duties; `workspace start`, `keys list` and the exact
  `DUTIES` tuple assertion still as stated.
- `scribe/cli.py` -> adds `scribe catalog bmad-estate`; `recall --mode/--scope/--kind` and `capture --type/--text`
  unchanged.
- `pixi.toml` -> pyforge-guild now carries `pyforge-herald` (Story 63.6) and `pyforge-mason` (Story 72.1).
  Installed check: `.pixi/envs/pyforge-guild/bin/pyforge --help` prints `stations: doctor, herald, marshal, mason,
  scribe, steward` / `not installed here: atlas (-e pyforge-atlas), warden (-e pyforge-warden)`; `mason --help` lists
  recipe / package / environment / doctor.
- Corrected: the Guild env carries six stations, not four; atlas and warden are the ones outside it; the help
  commands and the mason example now run from pyforge-guild; added the `context` alias.

## 11. docs/how-to/troubleshoot-bmad-agent-loops.md (verified 2026-10-10)

- `marshal/cli/dispatch.py` -> Story 92.1: a dispatch run whose recorded worktree is gone and that never finished is
  stale — never live, skipped by the in-flight guard with an `MRS-DISP-065` warning, reported stale by `marshal status`
  and `fleet-picture`; resume / `dispatch-attach` refuse it with `MRS-DISP-023`; remedy is to move the run dir into
  `implementation-artifacts/dispatch-runs-quarantine/` and list it in that folder's README. Other changes (102.1
  verdict reuse, 100.1 paused-surface record, 95.1 ruff, 93.1 recall) do not touch the page's claims.
- `marshal/dispatch_supervisor/__main__.py` -> process-group liveness with `session_liveness_error` on heartbeats,
  ruff-group and environment.yaml / spec-frontmatter journal steps. The verify fix turn (MRS-GATE-001/015,
  MRS-DISP-060, one turn) is unchanged (`core/dispatch_verify_fix.py` untouched since 10-10).
- Corrected: Step 1 now explains stale dispatch runs, the two codes and the quarantine remedy.

---

## Outside my set (reported, not touched)

The final docs-currency run shows three warn lines on pages that are not mine and were not in the original 20:
`docs/tutorials/local-platform-development.md` (6 stale sources), `docs/explanation/the-detector-framework.md`
(1 dead reference), `docs/reference/bmad-estate-llms-full.md` (generated page with no `generator:` in
`docs/map.yaml`). Probably side effects of concurrent edits elsewhere (for example to `docs/map.yaml`); the lead
should route them.
# Story 30.4 — docs-currency review: reference, explanation, tutorial (8 pages)

Worktree: `exciting-faraday-1e4549-wt-preflight-warn-hygiene-2026-10-24` (branch
`preflight-warn-hygiene-2026-10-24`, HEAD 188386e912). Base commits for the diffs:
`42f4b5e9b5` (last commit on or before 2026-09-20) and `ff2455866b` (2026-09-19).
Every page below that carries a `verified:` key moved to 2026-10-24 only after the review
recorded here. Two pages (agent-instruction-notes, github-workflows) have no frontmatter; they
were flagged for dead references only, so there was no date to move.

Detector results after the edits (exit codes read directly, no pipe):
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency` → exit 0.
  The one remaining warn is `docs/reference/bmad-estate-llms-full.md` (no `generator:` in
  `docs/map.yaml`), which is outside this set. None of the 8 pages appears.
- `pixi run --frozen -e pyforge-guild governance-currency` → exit 0, "every skill, script and
  path named in 11 governed document(s) resolves".

---

## docs/tutorials/local-platform-development.md (verified 2026-09-20 → 2026-10-24)

Note: commits 82b15d56ea (78.1), 343bdf9a2e (67.5) and 86c59f9583 (91.1) had already edited this
page after 2026-09-20 without moving `verified:`. It already mentioned
`LANGFLOW_SUPERUSER_PASSWORD`, `pyforge-foundry-full(-stack)` and the stations index. I re-checked
every claim, including those edits.

- **pixi.toml** (touched 2026-10-24): `platform-dev` = features `python-agent-platform` +
  `platform-dev`. The `platform-dev` feature still carries postgresql >=17.11,<18, pgvector,
  redis-server, silo, helm, kubectl and django-debug-toolbar. `pyforge-foundry-full-stack`
  composes the `platform-dev` feature (plus `platform-object-storage`). `platform-ci-test` exists
  and carries playwright-python, checked in pixi.lock. Step 1 and the prerequisites hold. No
  correction needed.
- **src/platform/README.md** (touched 2026-10-01): adds the `LANGFLOW_SUPERUSER_PASSWORD` rule
  for compose (already on the page from 78.1), says any local boot that starts Langflow (an
  ASGI boot of `config.asgi`) needs it, and adds IdP revocation on the next request.
  Corrected: Step 4 now says `runserver` serves the WSGI app (`WSGI_APPLICATION`, no daphne in
  INSTALLED_APPS), so the `/langflow/` ASGI mount is not there; an ASGI boot mounts it and
  needs the password.
- **src/platform/config/settings/base.py** (touched 2026-10-11): `LANGFLOW_AUTO_LOGIN` forced
  False, `LANGFLOW_SUPERUSER(_PASSWORD)` read from env, `SOCIALACCOUNT_STORE_TOKENS`, and
  `OBJECT_STORAGE_BUCKET/PREFIX` with no default. `DATABASE_URL` default `postgres:///platform`
  and `ADMIN_URL = "admin/"` are unchanged, and `manage.py` still defaults to the local leaf with
  `COMPONENT_RUNTIME=local`. Covered by the Step 4 sentence above; nothing else on the page
  relies on the rest.
- **src/platform/config/urls.py** (touched 2026-10-11): steward Story 91.1 added
  `stations/` → `stations_index` before the portal include. The page already names the index and
  its flag; checked against `flag-overlays.json`: on in dev, off in staging and production.
  `/cms/`, `/admin/` and the Lane 1 catch-all are unchanged. No correction needed.
- **.github/workflows/platform-ci.yml** (touched 2026-10-14): the `test` job gained "Install
  Chromium for the herald deck viewer browser check" (`python -m playwright install --with-deps
  chromium`, herald 30.2). Its steps are now check, Ruff, Ruff format, mypy, policy suite,
  sqlmigrate extraction and the full suite. It also gained ci-surface pause gates, Langflow
  smoke tests and chart flag inputs in other jobs, none of which the page relies on.
  Corrected: Step 5 now names Chromium and Ruff format, adds the one-time `pixi run -e
  platform-ci-test python -m playwright install chromium` (the deck-viewer test calls
  `chromium.launch()` once playwright imports), and points at the local twin
  `pixi run -e pyforge-guild platform-ci-local -- --test` (the `guild-tasks` task named in
  AGENTS.md) for the full step-for-step replay.
- **docs/dreams/platform-dev-boots-local.md** (touched 2026-10-04): a frontmatter-fence fix
  only. No change the page relies on.

## docs/reference/agent-instruction-notes.md (no frontmatter; dead reference only)

- Dead reference `docs/specs`: the legacy intake folder was emptied and the tier retired by
  doctor Story 37.1 on 2026-10-10 (`070f73edad`/`c9e4f1539c`; files under `archive/docs/specs/`,
  `feedstock-refresh.md` moved into `spec-pyforge-mason`). The page is the verbatim record of
  what AGENTS.md and CLAUDE.md said before 2026-09-26, and its intro says so. Fixed by wrapping
  the five citations (PR-gates item 1, the Tier rules paragraph, and the § *Intake specs* heading
  plus its legacy blockquote) in `<!-- governance-currency:ignore-start (the legacy intake tier,
  quoted as it stood; emptied 2026-10-10, its files now under archive/docs/specs/) -->` /
  `ignore-end` markers. The verbatim text is unchanged. The marker inside the numbered list is
  indented so the list still renders as one list.

## docs/reference/agent-memory-lifecycle.md (verified 2026-09-20 → 2026-10-24)

- **.claude/memory/MEMORY.md** (touched 2026-10-24): only entries were added. It is 118
  lines, still under the 200-line rule the page states, and the page's example entries
  (fleet-inbox, fleet landing-pass liveness) are still present. No correction needed.
- **src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py** (touched 2026-10-08): adds
  `scribe catalog bmad-estate` and catches OSError in capture. The capture flags (`--type`,
  `--text`, `--promote`, `--transcripts`, `--source`) are unchanged. Recall `--mode` / `--kind` /
  `--scope` already existed at the verified date but the page left them out, and AGENTS.md
  § *Scribe recall* now leads with `--mode planning`. Corrected: the Recall paragraph now says
  default recall leaves out code nodes, names `--mode planning|memory|code` / `--kind` (they
  cannot be combined) and `--scope <slug>`, and says AGENTS.md names `--mode planning` for team
  decisions.
- **CLAUDE.md** (touched 2026-10-10): trimmed by scribe 21.1 (2026-09-26). The bare
  `@AGENTS.md` and `@.claude/memory/MEMORY.md` imports the page cites are still there (lines 9
  and 52). No correction needed.
- **AGENTS.md** (touched 2026-10-15): marshal 46.3 (2026-09-24) made "the session-close ritual,
  in every harness, `scribe capture` and `marshal context advisory`" (verb confirmed in
  `pyforge/marshal/cli/context.py`). The agents-md 2.1.277 / `claude-md-and-agents-md` sentence
  still matches. Corrected: added Integration requirement 3, which closes each session with
  `scribe capture` and `marshal context advisory`.
- **docs/how-to/configure-your-coding-agent.md** (touched 2026-10-08): the prerequisite is now
  `pixi install -e pyforge-foundry-full`, which includes the Guild env. `scribe` still runs from
  `pyforge-guild` (`pyforge-scribe` is in the guild feature). No correction needed.

## docs/reference/github-workflows.md (no frontmatter; dead references only)

- Dead reference `docs/dashboard/kedro-viz`: the claim is true (pages.yml downloads into that
  folder, and `.gitignore:1038` ignores it), but the folder is absent from a checkout and the
  detector strips the trailing slash before `git check-ignore`, so the path cannot resolve.
  Fixed: the text now reads "the gitignored `kedro-viz/` folder under `docs/dashboard/`"
  (`docs/dashboard/` exists).
- Dead reference `.github/workflows/staged-recipes-linter.yml`: it sat in the "Where the pixi
  floor lives" list, which was wrong throughout (0.76.2 and seven sites; today the floor is
  `>=0.80.0` and the sites live in `scripts/pixi_version_registry.py`, and the linter was retired
  by Story 99.7 on 2026-10-14). Fixed by rewriting the section to point at the registry,
  summarise its site classes, and name `pixi run -e pyforge-guild pixi-version-check` (the
  guild-tasks feature) and `pixi run -e local-recipes bump-pixi-version`. The
  sync-pypi-mappings v0.59.0 incident stays as history, with the still-true note that its
  schedule stays off until one dispatch is green (checked in the workflow header).
- Adjacent stale line in the same area: § *Upstream divergence* described the two synced
  workflows in the present tense. It is now marked as history up to their 2026-10-14
  retirement. No other section was changed.

## docs/explanation/pyforge-ecosystem-architecture.md (verified 2026-09-20 → 2026-10-24)

- **src/platform/config/urls.py** (touched 2026-10-11): only the stations index was added; the
  page's host claims (Django + Wagtail, the isolation rule) hold. No correction needed.
- **src/platform/compose/compose.yml** (touched 2026-10-02): the postgres image is now
  `pgvector/pgvector:pg17`, the stack needs `LANGFLOW_SUPERUSER_PASSWORD`, and local cookies are
  insecure. Langflow is still mounted in the platform app (`langflow_integration`) and DB-GPT is
  still a sidecar (`dbgpt` service). No change the page relies on.
- **src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py** (touched 2026-10-08): adds
  `NOUN_ALIASES` (`context` → marshal, marshal 46.1), "not installed in this environment; it runs
  in -e pyforge-<station>" for a roster station that is missing, and a "not installed here" line
  in `--help`. Corrected, see below.
- **src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py** (touched 2026-10-15):
  `workspace start` still exists (the page's example command). No correction needed.
- **pixi.toml** (touched 2026-10-24): the `pyforge-guild` feature carries `pyforge-doctor`,
  `-herald`, `-marshal`, `-mason`, `-scribe`, `-steward` (herald was already there on
  2026-09-20, and mason arrived with steward 72.1). `pyforge-foundry-full` (steward 67.1,
  2026-09-26) carries all eight. Corrected: the page claimed four console scripts in the Guild
  env and that herald and mason were only in their own envs. It now lists the six, says the
  router names the env for warden and atlas, says `pyforge-foundry-full` carries all eight, and
  notes the `pyforge context …` alias.

## docs/explanation/pyforge-estate-overview.md (verified 2026-09-19 → 2026-10-24)

- **docs/dreams/pyforge-charter.md** (touched 2026-10-10): adds the BMAD-vocabulary cross-walk
  (steward 59.3) and its amendment entry. The station table, the "hand that builds" invariant,
  the "wrap, never reimplement" invariant and the Dream-first claims are unchanged. No change the
  page relies on.
- **docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md** (touched 2026-09-29): §11, one
  archive home (CAP-11). The page makes no fold or archive claim. No correction needed.
- **src/platform/config/urls.py** (touched 2026-10-11): the stations index. Corrected: Lane 2
  now notes the optional `/stations/` index (steward 91.1, flag `pyforge.steward.stations_index`,
  on in dev only, falling through to Wagtail when off). `/cms/` and the Wagtail catch-all are
  unchanged.
- **src/platform/deploy/charts/platform/values.yaml** (touched 2026-10-07): the postgres image
  is now pgvector pg17 (still 17), there is a required `LANGFLOW_SUPERUSER_PASSWORD`, a
  `flags.environment` and overlays (76.1), and a consumed `objectStorage` block (steward
  74.1/74.2). The Liquibase hook Job claim still holds. Corrected: the "backed by PostgreSQL and
  Redis" sentence now adds the optional consumed S3-compatible object store behind
  `pyforge.steward.object_store_consumer` (the chart names the bucket and prefix and never
  deploys a store). The `langflow_schema` / `dbgpt_schema` names were re-checked in
  settings/base.py.
- **src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py** (touched 2026-10-08): the
  page's one claim (unified `pyforge <station> <noun> <verb>` router) holds. No correction
  needed.
- **src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py** (touched 2026-10-02):
  Story 75.1 adds GHE credentials and `keys exec` behind a flag. Encryption still shells out to
  `age` (lines ~490/510). No correction needed.
- **docs/how-to/one-chain-station-ops.md** (touched 2026-10-08): a bare `sprint-ledger-sync` now
  repairs feed-behind-twin drift, and `--allow-regression` is the escape. Corrected: the
  Governed Execution note now gives `sprint-ledger-sync -- --project <station>` and says
  `bmad-spec` runs after a memlog append (AGENTS.md § Policy).

## docs/explanation/the-detector-framework.md (verified 2026-09-20 → 2026-10-24)

- **scripts/detectors.py** (touched 2026-10-17):
  - Story 99.1 also scans `scripts/ci_surface_gates.py`, which is outside the `*_check.py`
    pattern.
  - Doctor 49.1 (`_runs_detector`): a task matches only when its command runs the script's
    repo-relative path as one shell word. Before that it was `path.name in cmd`, so a test
    file's task passed.
  - New `--jobs` parallelism. The page does not cover flags, so it is not added.
  - New doctor rows in `_DOCTOR_SOURCE_TASKS`: fold-complete, bmad-output-hygiene,
    dreams-hygiene, frontmatter-duplicate-keys. Warn-only rows read `pass`, never `FINDINGS`.

  Corrected:
  - Added the extra scan target.
  - Added the path-as-one-shell-word rule.
  - Fixed "threads them in from `pyforge.doctor.sources.REGISTRY`". This was already inaccurate
    at the verified date. It uses its own `_DOCTOR_SOURCE_TASKS` list, calls each through
    `pyforge.doctor.sources.__main__.DISPATCH`, and filters by `scope_for` (REGISTRY).
  - Added that a source whose findings are all `warn` shows `pass` in the aggregate.
- **src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py** (touched
  2026-10-15):
  - New REGISTRY rows: ci-pause-drift, pages-liveness (runtime), fold-complete,
    frontmatter-duplicate-keys.
  - dreams-hygiene is now a DISPATCH name (41.1).
  - `degrade_on_exception` became the outer net of most gathers.
  - `locate_checkout_script` added.

  The page's REGISTRY/scope claims hold once the threading sentence above is fixed. No further
  correction.
- First re-run found a new dead reference I had introduced (`bmad-output-hygiene` matches the
  `bmad-*` skill pattern). It is fixed by naming the tasks `dreams-hygiene-check` /
  `bmad-output-hygiene-check`, which resolve as pixi ids.

## docs/explanation/the-tier-model-and-data-flow.md (verified 2026-09-20 → 2026-10-24)

- **AGENTS.md** (touched 2026-10-15):
  - The tier table is now 0 / 2 / 3. The Tier 1 row was removed by doctor 37.1 on 2026-10-10.
  - Story specs are drafted in Tier 3 and promoted to `planning-artifacts/specs/` after merge.
  - The ledger write path is the Tier-3 feed, then `sprint-ledger-sync -- --project <station>`.
  - Pitfall: only `implementation-artifacts/` is backlinked across worktrees.
    `planning-artifacts/` is per-worktree.

  Corrected:
  - Tier 1 is rewritten as retired.
  - Added the story-spec bullet under Tier 2.
  - The sync command now carries `-- --project <station>`, with a never-hand-edit note.
  - Added the shared-vs-per-worktree sentence to Tier 3.
  - The intro no longer says "four tiers" flatly.
- **docs/MAP.md** (touched 2026-10-15): the redirect-stub rows and Pages mounts changed. MAP.md
  itself still carries a Tier 1 `docs/specs/` row (line 26), which is outside my set (see the
  report). Nothing else on the page relies on it.
- **docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md** (touched 2026-09-29): §11, a
  Dream is live or archived, never both. A folded Dream moves to `archive/docs/dreams/` once its
  body is in the station Dream. Corrected: added that sentence to Tier 0.
- **scripts/promote_sprint_status.py** (touched 2026-10-08, marshal 54.1): a bare sync now
  repairs a feed that is behind the twin, names each repaired key, then promotes.
  `--allow-regression` is the only way out of `done`. Corrected: Tier 3's sync sentence now says
  so.
- **_bmad-output/PROJECTS.md** (touched 2026-10-10): one path repoint in the deckcraft row
  (`docs/specs/presentation-deck.md` → `docs/how-to/presentation-deck.md`). No change the page
  relies on.
- **Dead reference `docs/specs`** (in the Tier 1 heading and body): fixed. The heading no longer
  names the folder. The one historical sentence that does is wrapped in
  `governance-currency:ignore-start (the retired legacy folder, named because it was removed)` /
  `ignore-end`.

---

## Outside my file set (not edited)

- `docs/MAP.md` line 26 still lists "Legacy intake specs (Tier 1) | `docs/specs/`" as a live
  folder. The folder has been gone since doctor 37.1 (2026-10-10). Neither detector flags it.
  It needs a one-row edit by whoever owns MAP.md.
# Story 30.4: Dream hygiene decision record (three classes, 57 warnings)

Worktree: `exciting-faraday-1e4549-wt-preflight-warn-hygiene-2026-10-24` (branch `preflight-warn-hygiene-2026-10-24`).
Scope: `dream-status-trailing-comment` (23), `kinship-wikilink-dead` (32), `realization-log-missing` (2).
38 Dream files changed under `docs/dreams/`, nothing else. `docs/dreams/README.md` and
`docs/dreams/pyforge-doctor.md` were not touched. Nothing committed, stashed or switched.

## How the detector matches (read before editing)

From `pyforge-doctor/src/pyforge/doctor/sources/chain.py`:

- `dream-status-trailing-comment` fires on any frontmatter line whose stripped text starts with
  `status:` and contains `#`.
- `kinship-wikilink-dead` scans the whole body after the frontmatter, not only `## Kinships`. It
  resolves `[[target]]` or `[[target|label]]` (the target is the part before `|`) against
  top-level `docs/dreams/*.md` stems only. A file under `docs/dreams/archive/` or the repo-root
  `archive/docs/dreams/` never resolves.
- `realization-log-missing` fires for pitched, specified, realized or archived Dreams with no
  line matching `^## (The )?Realization( log)?$`.

Cross-check: `status_body_consistency.status_comment_text` joins the status line's trailing
comment with the `#` lines that follow it. Moving the comment onto the next line gives that
detector the same text and the same line number, so its findings do not change.

## 1. dream-status-trailing-comment (23 files)

Rule applied: `status: <value>   # <comment>` became `status: <value>`, with `# <comment>` on
the next line. The value and the comment text did not change. Where indented continuation
comment lines already followed, the moved line took their indentation, so the comment still
reads as one block and the untouched continuation lines did not move. This matches the shape
already on main in `marshal-run-watch.md`, `library-catalog-manifest-sync.md` and
`run-state-one-publisher.md`. Single-line comments go at column 0. No key was added or
duplicated.

| File | Value kept | Moved-comment indent |
|---|---|---|
| adaptive-model-tiering.md | archived | 19 (2 continuation lines follow) |
| asgi-multiplexer-monolith.md | archived | 0 |
| bmad-cursor-interactive-routing.md | archived | 19 |
| bmad-eval-quality.md | archived | 0 |
| bmad-method-core-upgrade.md | archived | 0 |
| bmad-suite-channel-product.md | archived | 0 |
| bmad-suite-install-class-wiring.md | archived | 0 |
| bmad-suite-metapackage.md | archived | 0 |
| cursor-native-tier-map.md | archived | 19 |
| db-gpt-django-plugin.md | archived | 0 |
| developer-machine-bootstrap.md | archived | 0 |
| dispatch-tier-routing-fails-safe.md | archived | 19 |
| enterprise-multi-agent-orchestration.md | archived | 0 |
| intelligence-hub.md | archived | 20 |
| langflow-django-plugin.md | archived | 0 |
| local-ocp-hybrid-environment.md | archived | 0 |
| mcp-era-isolation.md | archived | 0 |
| mcp-host-real-station-tools.md | archived | 20 |
| multi-repo-workspaces.md | archived | 0 |
| ocp-as-a-portability-profile.md | archived | 0 |
| platform-fifteen-factors.md | archived | 0 |
| pyforge-charter.md | specified | 0 |
| token-economy-claude-session-path.md | archived | 19 |

## 2. kinship-wikilink-dead (32 links, 14 files)

### Where each dead target went (evidence)

| Dead slug | History | Current holder | Treatment |
|---|---|---|---|
| `deckcraft`, `design-code-bridge`, `modernist-identity`, `video-scripts` | Seeded 2026-07-23 (`46e0b7d7cd`, `39a65489db`; video-scripts `c659043efa` 2026-08-01). Deleted 2026-08-01 by `409b3357bd`, whose message says all five were consolidated into the new `herald-pitch` Dream / `spec-herald-pitch`. Copies are in repo-root `archive/docs/dreams/`. `herald-pitch.md` is itself `archived`: *"Consolidated into [[pyforge-herald]] on 2026-09-17"*, narrative in pyforge-herald since 2026-08-02. `pyforge-herald.md` § What is real names all four: "design-code-bridge + deckcraft + video-scripts + modernist-identity … lived in `spec-herald-pitch`"; spec-deckcraft is now HER-5. | `pyforge-herald` | Retarget with an alias: `[[pyforge-herald|<slug>]]` |
| `pyforge-genesis` | Seeded 2026-07-23 (`46e0b7d7cd`). Deleted 2026-08-08 by `a3b5fefae8` ("charter: absorb pyforge-genesis"). `pyforge-charter.md` § *Satellite: The Seed* says it was "Absorbed 2026-08-08 from the retired `pyforge-genesis` Dream … The name retires, the content does not." Copy in `archive/docs/dreams/pyforge-genesis.md`. | `pyforge-charter` | Retarget `[[pyforge-charter|pyforge-genesis]]`, but unlinked to backticks inside the Charter itself, where a link would point at its own page |
| `presentation-deck` | Never a Dream file (no git history under `docs/dreams/`). It is `docs/how-to/presentation-deck.md`, which `pyforge-unifying-strategy.md` already calls "a legacy Tier-1 spec, not a Dream". | none (a how-to) | Relative markdown link `[presentation-deck](../how-to/presentation-deck.md)`; the file exists |
| `data-visualization-dashboards` | Never a Dream file here (no history). The prose calls it the "source dream" whose "WF source" describes the pattern, which is a sibling org's (WFT) Dream. | none | Unlinked to `` `data-visualization-dashboards` `` |
| `developer-workspace-management` | Never a Dream file here (no history). The prose names "a sibling org's `bmad-workspace-integration` dream" and the capability it depends on, which this repo "doesn't have yet". | none | Unlinked to `` `developer-workspace-management` `` |
| `intelligence-before-foundry` | Never a file anywhere. `git log --all -S` finds it only in `932d03da84` (2026-09-13), the commit that wrote this one line. No fold banner, no rename, no other mention in the repo or its history. | none | Item dropped: a bare slug with no gloss in a Kinships list says nothing once the link is gone |

Why an alias rather than a bare retarget: a bare `[[pyforge-herald]]` would change the sentence.
For example, "presenton-pixi-image and pyforge-herald — the two air-gapped application
expressions" is false. `[[target|label]]` moves the link and keeps the words. The detector's
regex accepts this form (`\[\[([^\]|]+)(?:\|[^\]]+)?\]\]`), and no other code in the repo parses
wikilinks (searched `src/`, `scripts/`, `.claude/scripts/`, `_bmad/scripts/`, `docs-site/`). No
retargeted line is a markdown table row, so the `|` cannot break a table.

Why backticks when unlinking: the repo writes a non-link slug that way, for example
"folded from `herald-pitch`", "the retired `pyforge-genesis` Dream" and "a sibling org's
`bmad-workspace-integration` dream". The words stay the same and still read as a name.
Backticked bare slugs match none of docs-currency's skill, script or path token regexes.

### Per link

| # | File:line | Was | Now | Why |
|---|---|---|---|---|
| 1 | atlas-query-dashboards.md:29 | `[[data-visualization-dashboards]]'s WF source` | `` `data-visualization-dashboards`'s WF source `` | sibling-org Dream, never here |
| 2 | bmad-switch-scope-enforcement.md:80 | `([[developer-workspace-management]]-shaped)` | `` (`developer-workspace-management`-shaped) `` | sibling-org capability, never here |
| 3 | enterprise-airgap.md:36 | `**[[deckcraft]]**` | `**[[pyforge-herald|deckcraft]]**` | deckcraft → herald-pitch → pyforge-herald |
| 4 | enterprise-airgap.md:49 | `([[pyforge-genesis]]` | `([[pyforge-charter|pyforge-genesis]]` | absorbed into Charter § Satellite: The Seed |
| 5 | factory-console.md:64 | `[[modernist-identity]] (a candidate restyle…` | `[[pyforge-herald|modernist-identity]]` | Modernist identity is held by pyforge-herald |
| 6 | genesis-installer.md:35 | `[[pyforge-genesis]] is the operating model` | `[[pyforge-charter|pyforge-genesis]]` | Charter holds the seed |
| 7 | genesis-installer.md:77 | `Splitting this out of [[pyforge-genesis]]` | `[[pyforge-charter|pyforge-genesis]]` | same; the historical words are kept |
| 8 | genesis-installer.md:184 | `split from [[pyforge-genesis]]` | `[[pyforge-charter|pyforge-genesis]]` | same |
| 9 | herald-pitch.md:559 | `[[design-code-bridge]]` | `[[pyforge-herald|design-code-bridge]]` | consolidated here 2026-08-01, then this Dream went into pyforge-herald, which names it |
| 10 | herald-pitch.md:559 | `[[modernist-identity]]` | `[[pyforge-herald|modernist-identity]]` | same |
| 11 | herald-pitch.md:559 | `[[deckcraft]]` | `[[pyforge-herald|deckcraft]]` | same |
| 12 | herald-pitch.md:559 | `[[video-scripts]]` | `[[pyforge-herald|video-scripts]]` | same |
| 13 | herald-pitch.md:559 | `[[presentation-deck]]` | `[presentation-deck](../how-to/presentation-deck.md)` | a how-to / legacy Tier-1 spec, never a Dream |
| 14 | presenton-pixi-image.md:59 | `Division of labor with [[deckcraft]]` | `[[pyforge-herald|deckcraft]]` | deckcraft → pyforge-herald |
| 15 | pyforge-charter.md:72 | `([[design-code-bridge]])` | `([[pyforge-herald|design-code-bridge]])` | design-code-bridge → pyforge-herald (the herald CLI) |
| 16 | pyforge-charter.md:1048 | `[[pyforge-genesis]], the operating-model seed` (quoted old §5) | `` `pyforge-genesis`, … `` | the Charter is the absorber, so a link would point at its own page; quoted history |
| 17 | pyforge-charter.md:1117 | `**[[pyforge-genesis]] stays**` | `` **`pyforge-genesis` stays** `` | same: a link to its own page, historical amendment text |
| 18 | pyforge-marshal.md:2779 | `([[developer-workspace-management]]-shaped)` | backticks | folded copy of #2 |
| 19 | pyforge-marshal.md:3204 | `[[modernist-identity]] (a candidate restyle…` | `[[pyforge-herald|modernist-identity]]` | folded copy of #5 |
| 20 | pyforge-marshal.md:5543 | `Piloted on [[design-code-bridge]]` | `[[pyforge-herald|design-code-bridge]]` | folded copy of regenerable-factory |
| 21 | pyforge-marshal.md:5546 | `[[modernist-identity]],` | `[[pyforge-herald|modernist-identity]],` | same |
| 22 | pyforge-marshal.md:5568 | `[[pyforge-genesis]] (the operating model this completes…` | `[[pyforge-charter|pyforge-genesis]]` | same |
| 23 | pyforge-steward.md:3624 | `**[[deckcraft]]**` | `**[[pyforge-herald|deckcraft]]**` | folded copy of #3 |
| 24 | pyforge-steward.md:3637 | `([[pyforge-genesis]]` | `([[pyforge-charter|pyforge-genesis]]` | folded copy of #4 |
| 25 | regenerable-factory.md:41 | `Piloted on [[design-code-bridge]]` | `[[pyforge-herald|design-code-bridge]]` | first Dream-first bmad-spec run was SPEC-design-code-bridge, now under pyforge-herald |
| 26 | regenerable-factory.md:44 | `[[modernist-identity]],` | `[[pyforge-herald|modernist-identity]],` | → pyforge-herald |
| 27 | regenerable-factory.md:66 | `[[pyforge-genesis]] (the operating model…` | `[[pyforge-charter|pyforge-genesis]]` | → Charter |
| 28 | scribe-code-navigation-owner.md:41 | `[[marshal-token-economy]] · [[intelligence-before-foundry]]` | `[[marshal-token-economy]]` | dropped: no target ever existed, and the bare slug has no gloss. I did not guess `intelligence-hub`, since nothing in the tree or history ties the two. |
| 29 | sentinel.md:49 | `**[[modernist-identity]]**` | `**[[pyforge-herald|modernist-identity]]**` | design-tokens pipeline → Modernist, held by pyforge-herald |
| 30 | sentinel.md:50 | `**[[deckcraft]]**` | `**[[pyforge-herald|deckcraft]]**` | → pyforge-herald |
| 31 | unity-data-stack.md:43 | `Where [[pyforge-genesis]] installs the *operating model*` | `[[pyforge-charter|pyforge-genesis]]` | the Charter's Seed: "the bootstrapper that installs the operating model anywhere" |
| 32 | unity-data-stack.md:62 | `[[pyforge-genesis]] (the installer would bootstrap Unity instances)` | `[[pyforge-charter|pyforge-genesis]]` | same. The Seed section also routes the installer half to the Marshal. |

Folded copies were changed identically: enterprise-airgap and pyforge-steward,
bmad-switch-scope-enforcement and pyforge-marshal, factory-console and pyforge-marshal,
regenerable-factory and pyforge-marshal. The paragraph text in each pair still matches, which
matters to `fold-complete` if those files later move to `archive/docs/dreams/`.

## 3. realization-log-missing (2 files)

Both logs are appended at the end of the file, dated YYYY-MM-DD, built only from the file's own
text and `git log --follow`. Each entry cites the commit it rests on.

- **docs-shelf-alignment.md**
  - 2026-09-14: seeded (`4e533c54e7`); Spec `ready` and Epic 23 decomposing CAP-1..7 the same day (the file's own § Settled 2026-09-14).
  - 2026-09-17: folded into [[pyforge-doctor]] (`4d3ae19674`): specified → archived, `archived-reason: folded-into-station-dream`, banner added.
  - 2026-10-10: the agentic-sdlc Kinship path repointed to `archive/docs/intake/agentic-sdlc/` by doctor Story 37.1 (`c9e4f1539c`).
  - 2026-10-24: log added (Story 30.4); no status change.
- **fleet-hygiene-verification-exemplar-program.md**
  - 2026-08-15: seeded (`92355c3eba`) with the EXEMPLAR-STANDARD refresh; the hygiene-sweep angle converged into `spec-deferred-work-visibility` CAP-8/9 (`2ffa858b5d`); the INV-A blind spot (`DW-CHAIN-COMPLETENESS-1`) added to Category 1 (`fbde190a47`).
  - 2026-09-05: `title:` added by the dreams-hygiene sweep (`e4016f4aa1`); status stayed `dreamt`.
  - 2026-09-17: folded into [[pyforge-doctor]] (`4d3ae19674`): dreamt → archived, `archived-reason`, `type: dream` and the banner added.
  - 2026-10-24: log added (Story 30.4); no status change.

## Verification (worktree root, exit codes read directly, never piped)

| Command | Exit | Result |
|---|---|---|
| `pixi run --frozen -e pyforge-guild dreams-hygiene-check` | 0 | `ok -- every Dream passes … Kinship wikilinks, table sync, and realization-log presence` |
| `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources dreams-hygiene` | 0 | one `ok` line, zero findings in any class. `dream-readme-missing` is also clear, from the other worker's README rows. |
| `pixi run --frozen -e pyforge-guild dream-chain-check` | 0 | `ok -- every Spec links a Dream, every Dream has a Spec …` |
| `pixi run --frozen -e pyforge-guild frontmatter-duplicate-keys-check` | 0 | `ok`. Note: this task reads story specs only, not Dreams. |
| ad hoc top-level duplicate-key and trailing-comment scan of the 25 edited frontmatters | n/a | 0 problems |

## Observation outside scope (not fixed)

On main, `marshal-run-watch.md`, `library-catalog-manifest-sync.md` and
`run-state-one-publisher.md` start their status comment mid-sentence. The 2026-09-16 marshal
fold (`1e845b55fc`) replaced each `status: … # <first line>` with a bare `status: archived` and
deleted the first comment line instead of moving it. For marshal-run-watch that line was
`# 2026-09-15 — spec-marshal-run-watch is `ready` (CAP-1..5; CAP-1+CAP-2 is`. The lost lines
can be recovered from `git show 1e845b55fc^:<path>`. These files were not in this worker's
findings, so they are untouched.
