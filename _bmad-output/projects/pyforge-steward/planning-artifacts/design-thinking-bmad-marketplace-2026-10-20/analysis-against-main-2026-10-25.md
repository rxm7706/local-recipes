# Marketplace re-check against main — 2026-10-25

Compared the marketplace reset (Epic 109, CAP-169–173, FR-42–46) with `origin/main` at `81f66ee411`, merged into this branch as `1d01035fc3`. No new Dream. Steward stays the owner.

## What main changed that touches this work

No new station. The packages are still atlas, core, doctor, herald, marshal, mason, scribe, steward, testing-kit, and warden. No new directory under `.claude/skills/`. The estate copies of `mason-environment`, `mason-package`, and `pyforge-warden` did not change. `.github/workflows/pages.yml` did not change on main. `pyforge.cutover_root` has not flipped. Epic 44 file-move stories 44.4–44.6 stay parked; the other unfinished 44.x rows stay blocked until the operator flips them. The marketplace path `docs/foundry/marketplace/` still matches the foundry target tree in `AGENTS.md`.

Main did land work beside the marketplace:

- **Atlas Epics 34, 35, 37, and 38.** The Pages data build keeps a last-good copy (37.12). A vulnerability feed that cannot be reached keeps its last good copy (34.12). The CVE watcher reads a history and marks a stale diff (37.5, 37.13). Boards for release cadence, archived-package alternatives, PURLs, and mapping gaps filled in. This is the fleet view of stale and vulnerable dependencies. It is not a skill a teammate copies.
- **Marshal Epic 103 / Story 103.1.** `marshal-mcp` starts on the official SDK, and preflight proves it. That is an operator server, not a marketplace listing.
- **Mason Story 26.2.** Conda-forge-expert tests no longer fetch conda-smithy's remote lint data. It does not change `@mason/environment` or `@mason/package`.
- **Steward Stories 13.6, 71.12, and 71.13.** A workspace started from another branch is landed once that branch is on main. A cancelled preflight lane names what stopped it. A second SIGINT does not deadlock the handler. Useful when a teammate later opens a skill pull request. Not an install path.
- **Doctor Stories 30.4 and 30.5.** Docs-currency tells a generator that cannot run from a stale page, and stops flagging true references. Marketplace markdown must stay a real reference. It does not add a skill.

Steward's own numbers were still free. Main's highest steward CAP heading is CAP-168, the kernel FR space on main ended at FR-41, and there is no Epic 109 on main. Marshal has its own CAP-169–173 (dispatch, harness run id, merge subjects). Those are `pyforge-marshal:CAP-*`, not `pyforge-steward:CAP-*`. Epic 109, FR-42–46, and CAP-169–173 stay.

## What is still valid

- This monorepo hosts and publishes the marketplace. There is no dedicated repository. `edit_store.mirrors` is `{host, repo}` and starts empty. `dedicated_repo` is rejected.
- The tree stays `docs/foundry/marketplace/`. Foundry rebuilds CAP-169–173 at cutover. Nothing moves at the `cutover_root` flip.
- Pages stays the existing `pages.yml` mount at `/marketplace/`, plus one zip per skill on the rolling `pages-site` release, while `pyforge.steward.marketplace_pages` is on.
- The v1 audience is still a teammate on Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin, or with no AI tool yet. Install is still a copy into `.claude/skills/<scope>-<slug>/` and `.agents/skills/<scope>-<slug>/`.
- Install sources are still a GitHub release, the Pages URL, or Artifactory. None of the three pilots is published, so the cards name `pyforge-mason`, `pyforge-warden`, and `pyforge-core` as unpublished.
- Trust stays `tier: community` / `trust_tier: unverified`. All three pilots stay `lane: code-backed`. Instructions-only remains a skill with no package.
- The success signal stays: a teammate other than rxm7706 contributes a skill, and a different teammate installs and uses it.
- The pain points are still the reason for the pilot: tribal knowledge, vulnerable or stale dependencies, broken environments, publishing internal packages, and lost team decisions. Atlas now shows the fleet side of the dependency pain. The three seed skills are still the teammate-facing answer, and they still stop where the packages are unpublished.
- Stories 109.1–109.3 (brief, three portable skills, marketplace tree and pointers) still match the tree. Stories 109.4 (`bmp`, including `bmp new skill --from-session`) and 109.5 (Round 0, then the Wizard-of-Oz pilot) are still the unbuilt sequence.

## What main made easier, and what it did not obsolete

Easier: a later contribution pull request can use `steward workspace` and Story 13.6's landing rule, and a red preflight now names the cancelled lane. The Pages site already carries atlas's dependency boards, so Round 0 does not need to invent a CVE dashboard. The skill text on main did not drift, so the portable copies did not need a rewrite in the merge.

Not obsolete: `bmp`, the desk test, the internal-mirror question, and the unpublished packages. Atlas boards and `marshal-mcp` do not install a skill into a teammate's tool. The 2026-10-21 product brief is still the brief. Do not run `bmad-product-brief` again unless Round 1 notes contradict it.

## Roadmap

Numbers unchanged. No new story. 109.4 and 109.5 stay the next stories.

| Order | Story | Acceptance, after the 2026-10-25 re-check |
|---|---|---|
| Done in this PR, in review | 109.1 brief | The 2026-10-21 brief still states the audience, the two skill directories, steward as owner, and the success signal. |
| Done in this PR, in review | 109.2 three skills | `@mason/environment`, `@mason/package`, `@warden/scan`, each with `steps.md`, no `pixi run -e`. Unpublished packages stay named. |
| Done in this PR, in review | 109.3 tree and pointers | `docs/foundry/marketplace/`, Pages at `/marketplace/`, Claude `github` source with `path` and `sparsePaths`. |
| Next, one person | 109.5 Round 0 | Run the Round 0 runbook below in a repository that is not local-recipes. Write the dated note on `MANUAL-CHECKLIST.md`. |
| Then, 2–3 teammates | 109.5 Round 1 | Run the Round 1 runbook. Two teammates must install by the manual copy and use a skill before 109.4 starts. |
| After that gate | 109.4 `bmp` | `bmp install` copies a folder into both skill directories. `bmp new skill --from-session` stays behind the publish gate (one merge by someone other than rxm7706). |
| Only if Round 1 contradicts the brief | Amend the 2026-10-21 brief | Do not mint a second Dream and do not run a fresh `bmad-product-brief` before those notes exist. |

## Round 0 runbook (one person, one project)

1. Pick a repository that is not local-recipes and not a worktree of it. A toy project with a `pyproject.toml` is enough.
2. On the public GitHub remote, add the marketplace with the `github` source `rxm7706/local-recipes`, path `docs/foundry/marketplace/.claude-plugin/marketplace.json`, sparse paths `docs/foundry/marketplace/.claude-plugin` and `docs/foundry/marketplace/skills`. If `edit_store.mirrors` is still empty, do not invent a GHES URL.
3. Open `docs/foundry/marketplace/site/index.html` and one skill card. Confirm the card renders `steps.md` and names unpublished packages.
4. Copy that skill's folder to `.claude/skills/<scope>-<slug>/` and `.agents/skills/<scope>-<slug>/`.
5. Check the tool you actually have. Claude Code should see `.claude/skills/`. Devin should see `.agents/skills/`. Cursor and Copilot read both. Gemini CLI reads `.agents/skills/`. A person with no AI tool follows `steps.md` from the card alone.
6. Run `steps.md` from the top. Stop at the first unpublished `pyforge-*` package. Do not run `pixi run -e`. Do not use a path inside local-recipes.
7. Write a dated note on `MANUAL-CHECKLIST.md`: repository, tool, which skill, which step ran, which step stopped, and whether the card's unpublished list matched.

## Round 1 runbook (two or three teammates)

Who: not rxm7706. Draw from Claude Code, Cursor, Copilot in VS Code, Gemini, Devin, and no AI tool. P4's examples still fit: one Cursor user on conda or pip, one Copilot or Gemini user who publishes packages, one person with no AI tool.

1. A person answers "find a skill" with the card URL `/marketplace/` or the folder path. No `bmp` and no `marshal-mcp`.
2. A person copies the folder into both skill directories and names the unpublished package.
3. The teammate follows `steps.md` on a real task in their own project. The no-AI-tool teammate uses the steps alone.
4. A teammate who wants to add a skill gets `templates/SKILL.md` and `.github/PULL_REQUEST_TEMPLATE.md`. Nobody uploads. That stand-in is `@bmp/skillify`.
5. Each teammate fills one grid: likes, questions, ideas, changes, completed y/n, stuck point, tool, source, operator interventions.
6. Stop or rethink if nobody uses a seed skill on a real task. Start 109.4's `bmp install` only after two teammates installed with the manual copy and used the skill. Start lint only after three pull requests caught a real problem. Start `bmp publish` / `bmp new skill --from-session` only after one merge by someone other than rxm7706.

## Open questions, with a recommendation

| Question | Recommendation |
|---|---|
| Which internal GitHub or GHES mirror of local-recipes, and is mirroring the full repository allowed at work? | Operator decision. Leave `edit_store.mirrors` empty. Do not mirror the full tree, recipes included, until rxm7706 says that host may hold it. The Claude sparse checkout only needs `docs/foundry/marketplace/.claude-plugin` and `docs/foundry/marketplace/skills`. |
| Should `bmp install` vendor module trees (`DW-FU-60-1-4`) or only copy skill folders? | Copy skill folders only. `bmad-method install --custom-source` still finds 0 modules. Leave the deferred row open. |
| Per-tool agent adapters? | None until Round 0 shows a tool that does not read the plain folder. |
| `DW-FU-60-1`, `DW-FU-60-1-4`, `DW-FRR-60-1`? | Carry all three. This epic does not close them. |
| Unpublished `pyforge-*` packages? | Keep them unpublished in this PR. The cards must keep saying so. |
| List atlas CVE boards or `marshal-mcp` as marketplace skills? | No. Atlas is already on Pages. Marshal MCP is an operator server. Add a listing only if Round 1 asks to install one of them as a skill. |
| Run `bmad-product-brief` again? | No. The 2026-10-21 brief still matches main. Amend that brief only when Round 1 notes contradict it. |
| Renumber CAP-169–173, FR-42–46, or Epic 109? | No. Main did not take the steward numbers. Marshal's CAP-169–173 are a different station. |
| Apply the `maintenance` label? | The diff is outside `recipes/`. The label was not applied. That is still an operator choice. |

## Gaps and risks

- Round 0 has not been run. The skeleton can be reviewed, and it cannot yet claim a teammate install.
- An empty mirror list means work teammates have no GHES URL. The public `github` source is the only install form that works today.
- The three skills stop on unpublished packages. That is honest, and it means Round 0 cannot finish a lock, a build, or a scan inside the teammate's tool.
- Story specs for 109.4 and 109.5 say `ready-for-dev`. The epic lines and the sprint ledger say `backlog`. The merge did not change that split.
- Doctor's docs-currency check now reads generated pages more strictly. A future edit of marketplace markdown has to keep real links, including `templates/steps.md`.
