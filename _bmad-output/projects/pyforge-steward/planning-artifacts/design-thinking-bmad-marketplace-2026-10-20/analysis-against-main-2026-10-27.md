# Marketplace re-check against main — 2026-10-27

Compared the marketplace reset (Epic 109, CAP-169–173, FR-42–46) with `origin/main` at `b306864227`, merged into this branch as `aeebbcc293`. The previous re-check is `analysis-against-main-2026-10-25.md` (against `81f66ee411`, merge `1d01035fc3`). No new Dream. Steward stays the owner. No new story.

## What main changed that touches this work

No new station. The packages are still atlas, core, doctor, herald, marshal, mason, scribe, steward, testing-kit, and warden. No new directory under `.claude/skills/`. No new agent directory. The estate copies of `mason-environment`, `mason-package`, and `pyforge-warden` did not change. `.github/workflows/pages.yml` did not change on main. `pyforge.cutover_root` is still `local-recipes` in dev, staging, and production. Epic 44 is `in-progress`: 44.3, 44.7, 44.12, and 44.13 are `done`; 44.4, 44.5, and 44.6 are `backlog`; the other unfinished 44.x keys are `blocked`. The marketplace path `docs/foundry/marketplace/` still matches the foundry target tree in `AGENTS.md` (`src/packages/`, `factory/`, `skills/{stations,personas,domain}/`, `docs/foundry/`).

Main now knows this draft exists and numbered around it. Steward Epic 111 says Epic 109 is claimed here. Epic 112 and the PRD say CAP-169–173 and FR-42–FR-47 are claimed here. Main then took CAP-174 (Platform CI budget, Epic 112, FR-48) and CAP-175 (preflight and CI budget, Epic 117, FR-49). Kernel FR space on main is FR-1–FR-41 plus FR-48 and FR-49, with FR-50 called the next free id. This branch still defines only FR-42–FR-46. FR-47 is a hole main reserved and this PR does not fill.

Beside that numbering:

- **One chain (spec-one-chain-per-station CAP-11).** Archived Dreams left `docs/dreams/` for `archive/docs/dreams/`. The seed is now `archive/docs/dreams/self-hosted-bmad-marketplace.md`. Its 2026-10-21 revisit is in that file. `docs/dreams/README.md` no longer lists archived Dreams, so the marketplace row was not put back. The adoption register now lives in `spec-pyforge-steward`. Absorbed Spec folders moved to `archive/_bmad-output/`.
- **Steward CAP-175 / Epic 117.** A PR's CI answers inside a measured budget. `coverage-gates.yml` is retired. A station suite is package-local and live-tree halves, and the station jobs are sharded. Image builds and the conda-forge-expert regression net leave the pull-request path. `pyforge.steward.preflight_critical_path` is a kill switch on in every environment. A later skill pull request hits this shape. It is not an install path.
- **Steward CAP-174 / Epic 112.** The Platform CI test job installs the browser only when the image lacks it, and its budget covers a slow mirror. Same idea on the herald job. Not a listing.
- **Steward Stories 110.1 and 111.1.** FR-1–FR-31 name the capabilities that realize them, and the Spec's capability text was restored from the pre-fold source. The marketplace FRs were already `FR-n ← CAP-m`.
- **Mason Story 34.1.** The conda-forge atlas reads the bot's split graph repos. That is recipe-factory code, not a skill a teammate copies.
- **Doctor Epic 55.** The live-tree half of doctor's suite is its own job. Marketplace markdown still has to be a real reference.
- **Flags.** Main added a large set (marshal front door, loop homes, supervised runs, scribe's BMAD-estate catalog, atlas agent-pipeline tools, the preflight scheduler). None of them is a marketplace listing. `pyforge.steward.marketplace_pages` stays default off, dev on, staging off, production off.

The 2026-10-25 neighbors are still true: atlas Pages boards are the fleet view of stale and vulnerable dependencies, and `marshal-mcp` is an operator server.

## What is still valid

- This monorepo hosts and publishes the marketplace. There is no dedicated repository. `edit_store.mirrors` is `{host, repo}` and starts empty.
- The tree stays `docs/foundry/marketplace/`. Foundry rebuilds CAP-169–173 at cutover (mode `rebuild`). Nothing moves at the `cutover_root` flip.
- Pages stays the existing `pages.yml` mount at `/marketplace/`, plus one zip per skill on the rolling `pages-site` release, while `pyforge.steward.marketplace_pages` is on.
- The v1 audience is still a teammate on Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin, or with no AI tool yet. Install is still a copy into `.claude/skills/<scope>-<slug>/` and `.agents/skills/<scope>-<slug>/`.
- Install sources are still a GitHub release, the Pages URL, or Artifactory. The three pilots still name `pyforge-mason`, `pyforge-warden`, and `pyforge-core` as unpublished.
- Trust stays `tier: community` / `trust_tier: unverified`. All three pilots stay `lane: code-backed`.
- The success signal stays: a teammate other than rxm7706 contributes a skill, and a different teammate installs and uses it.
- The pain points are still the reason for the pilot: tribal knowledge, vulnerable or stale dependencies, broken environments, publishing internal packages, and lost team decisions. Atlas shows the fleet side. The three seed skills are still the teammate-facing answer.
- Stories 109.1–109.3 still match the tree. Stories 109.4 and 109.5 are still the unbuilt sequence.

## What main made easier, and what it did not obsolete

Easier: main left the numbers free on purpose, so this PR does not renumber. A later contribution pull request runs on the CAP-175 CI shape (sharded station jobs, coverage from the suite itself, image builds off the pull-request path unless the diff touches an image). The one-chain move puts the archived seed in one archive home, and the living chain stays the steward Dream. The Pages site still carries atlas's dependency boards, so Round 0 does not invent a CVE dashboard.

Not obsolete: `bmp`, the desk test, the internal-mirror question, and the unpublished packages. New flags, the conda-forge graph split, atlas boards, and `marshal-mcp` do not install a skill into a teammate's tool. The 2026-10-21 product brief is still the brief. Do not run `bmad-product-brief` again unless Round 1 notes contradict it.

## Roadmap

Numbers unchanged. No new story. 109.4 and 109.5 stay the next stories.

| Order | Story | Acceptance, after the 2026-10-27 re-check |
|---|---|---|
| Done in this PR, in review | 109.1 brief | The 2026-10-21 brief still states the audience, the two skill directories, steward as owner, and the success signal. The seed Dream path is `archive/docs/dreams/self-hosted-bmad-marketplace.md`. |
| Done in this PR, in review | 109.2 three skills | `@mason/environment`, `@mason/package`, `@warden/scan`, each with `steps.md`, no `pixi run -e`. Unpublished packages stay named. Main did not change those estate procedures. |
| Done in this PR, in review | 109.3 tree and pointers | `docs/foundry/marketplace/`, Pages at `/marketplace/`, Claude `github` source with `path` and `sparsePaths`. `marketplace_pages` stays dev on, staging and production off. |
| Next, one person | 109.5 Round 0 | Run the Round 0 runbook below in a repository that is not local-recipes. Write the dated note on `MANUAL-CHECKLIST.md`. |
| Then, 2–3 teammates | 109.5 Round 1 | Run the Round 1 runbook. Two teammates must install by the manual copy and use a skill before 109.4 starts. A contribution pull request is judged by the CAP-175 CI shape. |
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
4. A teammate who wants to add a skill gets `templates/SKILL.md` and `.github/PULL_REQUEST_TEMPLATE.md`. Nobody uploads. That stand-in is `@bmp/skillify`. The pull request they open is judged by the current CI: sharded station jobs, coverage from the suite run, and no image build unless the diff touches an image. `coverage-gates.yml` is gone.
5. Each teammate fills one grid: likes, questions, ideas, changes, completed y/n, stuck point, tool, source, operator interventions.
6. Stop or rethink if nobody uses a seed skill on a real task. Start 109.4's `bmp install` only after two teammates installed with the manual copy and used the skill. Start lint only after three pull requests caught a real problem. Start `bmp publish` / `bmp new skill --from-session` only after one merge by someone other than rxm7706.

## Open questions, with a recommendation

These three are pending rxm7706. This note does not decide them.

| Question | Recommendation, not a decision |
|---|---|
| Which internal GitHub or GHES mirror of local-recipes, and is mirroring the full repository allowed at work? | Leave `edit_store.mirrors` empty until rxm7706 names the host. Do not mirror the full tree, recipes included, before that. The Claude sparse checkout only needs `docs/foundry/marketplace/.claude-plugin` and `docs/foundry/marketplace/skills`. |
| Apply the `maintenance` label? | Closed 2026-10-28: the label is on PR #2274. The diff is outside `recipes/`, and § Policy requires it. |
| Story specs 109.4 and 109.5 said `ready-for-dev` while the epic status lines and the sprint ledger said `backlog`. | Closed 2026-10-28: commit `40d02b7da9` set both story specs to `backlog`, and CAP-172 and CAP-173 render their arrows as `(backlog)`. No `sprint-ledger-sync` was run. |

The rest, recommended and unchanged:

| Question | Recommendation |
|---|---|
| Should `bmp install` vendor module trees (`DW-FU-60-1-4`) or only copy skill folders? | Copy skill folders only. Leave the deferred row open. |
| Per-tool agent adapters? | None until Round 0 shows a tool that does not read the plain folder. |
| `DW-FU-60-1`, `DW-FU-60-1-4`, `DW-FRR-60-1`? | Carry all three. This epic does not close them. |
| Unpublished `pyforge-*` packages? | Keep them unpublished in this PR. The cards must keep saying so. |
| List atlas CVE boards, `marshal-mcp`, the new flags, or the conda-forge graph split as marketplace skills? | No. Add a listing only if Round 1 asks to install one of them as a skill. |
| Run `bmad-product-brief` again? | No. Amend the 2026-10-21 brief only when Round 1 notes contradict it. |
| Renumber, or fill FR-47? | No. Main reserved CAP-169–173, FR-42–FR-47, and Epic 109, and took the next ids. This PR keeps FR-42–FR-46. FR-47 stays unused. |
| Put the archived seed back in `docs/dreams/README.md`? | No. One-chain moved archived Dreams to `archive/docs/dreams/`. The living entry is the steward Dream. |

## Gaps and risks

- Round 0 has not been run. The skeleton can be reviewed, and it cannot yet claim a teammate install.
- An empty mirror list means work teammates have no GHES URL. The public `github` source is the only install form that works today.
- The three skills stop on unpublished packages. Round 0 cannot finish a lock, a build, or a scan inside the teammate's tool.
- The ready-for-dev versus backlog split on 109.4 and 109.5 closed on 2026-10-28: commit `40d02b7da9` set both story specs to `backlog`. No ledger sync was needed.
- FR-47 is reserved in main's PRD prose and undefined here. A later story must not assume FR-47 is free, and this PR must not invent it to close the hole.
- Doctor's docs-currency check reads generated pages strictly. Marketplace markdown has to keep real links, including `templates/steps.md`.
- The seed path `docs/dreams/self-hosted-bmad-marketplace.md` no longer exists. Current pointers use `archive/docs/dreams/self-hosted-bmad-marketplace.md`.
