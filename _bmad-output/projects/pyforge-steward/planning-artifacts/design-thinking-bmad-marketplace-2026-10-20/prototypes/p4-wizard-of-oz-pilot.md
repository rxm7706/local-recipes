# P4 — Wizard-of-Oz pilot (manual marketplace)

Goal: before building the automation, learn whether teammates **find, install, use, and contribute** skills when
the marketplace looks real but rxm7706 does review, CI, and promotion **by hand** behind the scenes.

## Who
- **2–3 teammates** with different tools and experience, e.g.:
  - T1: Cursor user, regular conda/pip work (the storyboard "Dana").
  - T2: Copilot in VS Code or Gemini user, publishes internal packages.
  - T3: no AI coding tool, or a new hire. Tests the readable-steps path.
- Not in the pilot: rxm7706 (operator), public users, bots.

## Seed listings (3)
1. `@mason/environment`: lock & check a mixed conda + pip env.
2. `@warden/scan`: dependency & vulnerability scan (offline vulnerability DB).
3. `@mason/package`: build & ship a package to Artifactory.
Optional 4th, if one teammate's pain is decisions: `@scribe/agent` in CLI-only mode, to test the agent + requires path.

Before the pilot: rewrite each SKILL.md off `pixi run -e …` and repo paths, and add a `steps.md`. That's real work;
without it the pilot only tests a fake.

## Real vs faked

| Part | Pilot | How |
|---|---|---|
| Skill content (SKILL.md, steps.md) | **Real** | Rewritten seed skills |
| Marketplace repo on internal GitHub | **Real** | One repo: `skills/<scope>/<slug>/` + `listing.yaml` |
| Pages skill cards | **Real but static** | P3 card hand-adapted per listing; one index page |
| Install | **Faked** | No `bmp` yet. Card shows a copy-paste script (`curl`/`unzip` from the release, or `conda install` + copy) into `.agents/skills` + `.claude/skills` |
| Artifactory package | **Real for one listing**, others GitHub zip only | Tests whether the source matters to them |
| Search / in-tool discovery | **Faked** | The index page plus a pinned "start here" message; rxm7706 answers "is there a skill for…?" in chat as if he were the search |
| Lint + clean-machine CI | **Faked** | rxm7706 runs the checks by hand (frontmatter, no repo paths, gitleaks, a fresh container install) and posts a "CI" comment on the PR |
| Review + promotion to estate-reviewed | **Faked** | rxm7706 approves, writes `reviews/<name>.yaml`, edits the badge on the card |
| `new` / "skillify this session" | **Faked** | Teammate asks their AI to "write a SKILL.md from what we just did" using a template file; rxm7706 helps shape it |
| `publish` | **Real PR**, manual steps | Teammate opens a PR to the repo; template PR description |
| `outdated` / update | **Faked** | rxm7706 bumps one listing mid-pilot and posts a changelog note; watch whether anyone updates |

## Tasks each teammate attempts
1. **Find:** "You need to lock this repo's env / scan its dependencies. Find out if the team has a skill for it."
   Don't tell them the URL beyond the one launch message.
2. **Judge trust:** "Would you let your AI tool run this? Why or why not?"
3. **Install** into one of their real work repos, from the source they prefer.
4. **Use** it on a real task in their own tool, or by following the steps (T3).
5. **Contribute one skill** from something they recently explained to someone else: draft it, open the PR, respond to the review.
6. (Optional) **Second-user moment:** another pilot teammate installs that contributed skill.

## What to observe
- Where they start looking (in the AI tool, chat, Pages, asking rxm7706).
- Time and steps to first successful run; where they stall or give up.
- Whether their tool actually picked up the skill from `.agents/skills` / `.claude/skills`, and whether they had to name it.
- Which install source they pick, and why.
- Which trust signals they read (owner, tier, verified date, steps) and which they ignore.
- What breaks on their machine that rxm7706's machine hides: paths, auth, OS, missing CLI.
- For T3: can they follow the steps on Pages unaided?
- Contribution: what stops them; how long the PR takes; what review feedback they needed.
- What rxm7706 did by hand, and how often. This sizes the automation.

## Feedback capture grid (one per teammate per task)

| Teammate / task | Likes | Questions | Ideas | Changes |
|---|---|---|---|---|
| T1 · find | | | | |
| T1 · install | | | | |
| T1 · use | | | | |
| T1 · contribute | | | | |
| T2 · … | | | | |
| T3 · … | | | | |

Also log per task: completed (y/n), stuck point, which tool, which source, operator interventions (count + what).

## Riskiest assumptions to test
1. Teammates want team skills in their AI tool at all, versus asking a person or reading a wiki.
2. One SKILL.md folder in `.agents/skills` + `.claude/skills` really works in each of their tools, unmodified.
3. Readable steps alone are enough for a no-AI teammate.
4. Trust signals (owner, review, verified date) are enough for them to let an AI run a code-backed skill.
5. Someone other than rxm7706 will contribute a skill if the path is a PR plus a template.
6. Install source matters (Artifactory vs GitHub), or teammates don't care as long as it's one command.
7. Agents add value beyond skills; "CLI-only" station agents are useful without the server.
8. Discovery needs to happen in-tool; a Pages link and a launch message aren't enough.

## Exit criteria — what to automate, and when
Automate a faked step once the pilot shows it is **wanted** and **repeatable**:
- **Build `bmp install` / `sync`** when ≥2 teammates have installed a skill via the manual script and used it in their own tool.
- **Build lint + clean-machine CI** when rxm7706 has run the manual checks on ≥3 PRs and they caught at least one real problem.
- **Build `bmp publish` / `new`** when ≥1 teammate other than rxm7706 has merged a skill.
- **Build search / MCP discovery** only if observation shows people look for skills inside their AI tool first.
- **Build generated per-tool manifests or agent adapters** only if a pilot tool failed to pick up the plain skill folder.
- **Stop or rethink** if no teammate uses a seed skill on a real task, or nobody contributes after being asked.
Success moment, same as the storyboard: a second teammate installs and uses a skill a first teammate contributed.
