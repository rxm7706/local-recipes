# Design Thinking: BMAD Skills & Agents Marketplace (reset)

Date: 2026-10-20
Facilitated with rxm7706

## Design Challenge

rxm7706's station agents and skills (atlas, doctor, herald, mason, ...) and BMAD modules are only usable inside the `local-recipes` repo. v1 (Epic 60) built catalog plumbing but has no own listings, a 0-modules installer bug, and no browse surface.

Primary user for v1: **teammates at work** (chosen over self-across-machines, public BMAD community, and AI agents/bots; those remain later audiences).

## Challenge Statement

How might we let rxm7706's teammates at work discover, trust, install and use his BMAD agents and skills from inside their normal work setup, without needing access to `local-recipes`?

Draft success bar: a teammate on a clean work machine adds the marketplace, sees at least 3 of rxm7706's listings, installs one, and runs it.

Constraints: (to be filled in)

Teammates' tools (mixed): Claude Code, Cursor, GitHub Copilot in VS Code, Devin (Cognition), Gemini (Google), and some with no AI coding tool yet.
Implication: a Claude-only marketplace.json (v1) reaches a minority; listings likely need a tool-neutral package format plus per-tool adapters. To verify: which tools natively read SKILL.md / AGENTS.md.

Constraints (work environment):
- Install channel: Artifactory (conda or pip packages)
- Source/review: internal GitHub or GitLab
- Browse surface: internal GitHub Pages deployment is available
- Fallback: copying files / shared drive
- Public GitHub NOT assumed available -> nothing may depend on github.com at install time (note: v1 listings all point at public GitHub; DW-FU-60-1-4)

## Empathize (in progress)

User: all stations (atlas, doctor, herald, marshal, mason, scribe) will have relevant skills and agents. Researching per-station value to teammates and portability to pick first 3-5 listings.

### Key observations (from repo + official tool docs, 2026-10-20)
- All six teammate tools read SKILL.md skill folders. `.agents/skills/` covers Cursor, Copilot, Devin, Gemini CLI, Codex; `.claude/skills/` covers Claude Code (and Cursor/Copilot). Installing into both reaches everyone.
- Marketplace formats are six incompatible per-tool formats; treat as optional add-ons, not the backbone. v1's Claude marketplace.json reaches only Claude Code.
- Custom agent formats differ per tool; shipping agents as skills is the portable route.
- Station agents depend on running station servers + CLI + _bmad/ folder: low portability today.
- Skill texts claim PyPI pyforge-<station> 0.1.0 packages; pypi.org returns 404 for core/mason/scribe/warden; no station conda recipes yet.
- Repo already packages skill bundles for conda (BMAD modules, agent-skills, karpathy-skills, kedro-skills, bmad-labs-skills); installers copy into .claude/skills/ only.
- Many generic engineering skills come from addyosmani/agent-skills (third party).

### Candidate first listings
1. Warden dependency & vulnerability scan (pyforge-warden): offline vuln DB mode
2. Mason environment lock & check (mason-environment + pyforge-mason): mixed conda+pip lockfile
3. Mason package build & ship (mason-package)
4. Scribe team memory (pyforge-scribe), optional; tied to .claude/memory
Prereqs: publish packages to Artifactory; rewrite skill text off `pixi run -e` and repo paths.

### User insights / pain points (rxm7706, 2026-10-20)
Teammates feel pain on ALL of:
- Vulnerable or out-of-date dependencies (Warden)
- Broken or unreproducible environments (Mason environment)
- Building and publishing internal packages (Mason package)
- Losing track of team decisions (Scribe)
- **Tribal knowledge**: know-how isn't captured as customized skills, specs, and steps, so work isn't automated or repeatable.

### Empathy map (draft)
- Says: "How did you set that env up?" "Who knows how to publish to Artifactory?" "Why did we pick X?"
- Thinks: AI tools could do this if they knew our way of working.
- Does: asks the one person who knows; copies snippets; rebuilds envs by hand; uses a mix of AI tools with no shared team context.
- Feels: blocked, dependent, re-inventing.

## Define

### POV statement (draft)
Teammates at work need their team's hard-won know-how (env setup, dependency hygiene, packaging, decisions) packaged as skills their own AI tool can run, because today that knowledge lives in a few people's heads and each person re-learns or waits.

### How Might We (draft)
1. HMW turn one person's working practice into a skill any teammate's AI tool can run, regardless of tool?
2. HMW make installing a team skill as routine as installing a package from Artifactory?
3. HMW let teammates trust a skill (who wrote it, was it reviewed, does it work here)?
4. HMW make contributing a new skill or spec easier than answering the same question twice?
5. HMW let someone with no AI tool still benefit (readable spec/steps on the internal Pages site)?
6. HMW keep skills current as practices change?

### Problem insights
- Distribution was v1's whole focus, but the bigger gap is capture + contribution.
- Every listing should double as human-readable steps (spec), so the Pages site serves non-AI teammates.
- rxm7706's stations are seed content; the product succeeds when a teammate publishes their own skill.

### Advanced elicitation on POV (Reframe, 5 Whys, Persona Focus Group, Pre-mortem, First Principles)

**Reframe the Question:** "tribal knowledge" is a symptom. Sharper problem: teammates' AI tools don't know how this team works, and writing it down costs more than re-answering.

**5 Whys:** re-learning -> know-how not written down -> writing skills/specs is extra work with no visible payoff and no standard place/format -> nobody finds or runs what's written, so it rots -> no owner and no check that it still works. Root causes: no low-effort capture path; no signal that a skill is used or still works.

**Persona focus group:**
- Senior engineer: won't write for six tools; won't let an AI run builds unreviewed -> one format, reviewed, dry-run/explain mode.
- New hire: doesn't know what exists or what to ask -> browse by task, a "start here" bundle.
- No-AI teammate: wants the steps -> every skill renders as a readable runbook on internal Pages.
- Team lead / security: who approved it, what does it touch, does it call out -> provenance, review record, offline, Artifactory-scanned.

**Pre-mortem (6 months, nobody uses it):** only rxm7706 contributed (bus factor recreated); install differed per tool and skills referenced pixi/repo paths and broke; security blocked executable scripts; a skill broke once and trust died; nobody knew it existed. Prevention: contributor path on day one, one install command, clean-machine CI per listing, versioned releases via Artifactory, announce in team channels, track installs/use.

**First principles:** reuse requires (1) discovery at the moment of need, ideally inside the AI tool; (2) zero-friction install within work constraints; (3) it works in their environment; (4) it's trusted; (5) contributing is cheaper than re-explaining. A browse catalog only partly covers (1). The product is a team skill library + contribution workflow; the browse site is secondary.

### Refined POV (APPLIED 2026-10-20)
Teammates at work need their AI tools, and themselves, to know how this team does things (env setup, dependency hygiene, packaging, the reasons behind decisions) at the moment they need it, because today that know-how lives in a few heads, writing it down costs more than re-explaining, and nothing shows whether written steps still work.

### Revised HMWs (APPLIED)
1. HMW capture know-how as a side effect of doing the work (from a session, PR, or runbook) rather than as extra writing?
2. HMW make one skill run in every teammate's tool and read as plain steps for those with none?
3. HMW make installing team skills one routine Artifactory command?
4. HMW prove a skill still works here (clean-machine check) and show who reviewed it?
5. HMW surface the right skill inside the AI tool when it's needed, not just on a website?
6. HMW make contributing a skill easier than answering the same question twice?

Proposed success signal: a teammate other than rxm7706 publishes a skill, and a different teammate installs and uses it.

Product reframe: a team skill library with a contribution path; the browse site is secondary.

### Elicitation round 2 (Steelmanning, Subtraction, Second-Order, Shark Tank, Constraint Injection)

**Steelmanning (don't build anything):** one internal git repo of SKILL.md folders + AGENTS.md; all six tools read .agents/skills; PRs are the review; Pages renders it; zero infra. Rebuttal: fails on per-project install and drift, versioned/offline installs, skills that need code dependencies, and proof it still works. Conclusion: the repo IS the backbone and contribution path; add only a thin versioned installer and CI.

**Subtraction (cut for v-next):** per-tool marketplace manifests as the core (keep as optional generated output), extra ship backends (object storage, git bundle), Frames, server-dependent station agents, product B (skillsctl) and C (billing), heavy steward gate (replace with PR review + CODEOWNERS), browse.yaml (replace with Pages generated from SKILL.md).

**Second-order thinking:** easy contribution -> uneven quality -> lint (frontmatter, no repo paths, no secrets) + verified badge. Auto-surfacing skills -> context bloat / wrong triggers -> opt-in bundles per project, not install-everything. Scripted skills -> security bottleneck -> two lanes: instructions-only fast lane vs code skills packaged and scanned via Artifactory. rxm7706 as sole owner -> bottleneck -> CODEOWNERS per area. Pinned versions go stale -> update command / changelog notice.

**Shark Tank pitch:** "One command gives your AI tool our team's way of doing envs, dependencies and packaging, and anyone can add theirs." Challenges: why not a wiki (not executable, rots; skills are run and CI-tested); who maintains (CODEOWNERS, contributor path); metric (contributors other than rxm7706, installs, fewer repeat questions); cost (reuses catalog.py, recipe pattern, internal GH/Pages/Artifactory); security (offline, scanned, instruction-only lane). Weak spot: no direct evidence yet that teammates want it -> pilot with 2-3 teammates first.

**Constraint injection:** "no installer allowed" -> a one-line clone/copy script works for instruction-only skills. "no custom code allowed" -> first listings could wrap standard tools teammates can already get from Artifactory instead of requiring unpublished pyforge-* packages (to verify per skill). Remove constraint: add packaged code only where it clearly adds value.

### Proposed direction changes (round 2)
1. Backbone: internal git repo of SKILL.md folders = source of truth + contribution via PR; CI lints and clean-machine tests each skill; Pages site generated from it (readable steps for no-AI teammates).
2. Thin versioned installer on Artifactory that copies chosen bundles into .agents/skills and .claude/skills; opt-in bundles per project.
3. Two lanes: instructions-only (fast) and code-backed (packaged, scanned).
4. Cut from v-next: per-tool marketplace manifests as core, extra ship backends, Frames, server-dependent station agents, products B and C.
5. Validate with a 2-3 teammate pilot before broad build.

### Direction (APPLIED with rxm7706's changes, 2026-10-20)
rxm7706: "we want to make all the BMAD-SKILLS, the Station Skills (Created using BMAD), the Agents (Created using BMAD) easy to find, install, and also for people to create and publish / contribute their own skills & Agents. So we do need a marketplace, and it can be hosted on github / github pages and installs can be directly from github / github pages or an artifactory"

Updated direction:
- It IS a marketplace. Scope: (a) BMAD skills/modules, (b) station skills built with BMAD, (c) agents built with BMAD; plus create + publish/contribute for teammates.
- Four jobs: find, install, create, publish.
- Hosting: GitHub repo + GitHub Pages (internal or public). Install sources: directly from GitHub/Pages OR Artifactory (both supported).
- Constraint update: GitHub is an allowed install source (supersedes earlier "public github.com not assumed").
- Carry forward from round 2: repo of skill/agent folders as source of truth with PR contribution, automated checks + clean-machine verification, Pages generated from the repo, installer into .agents/skills and .claude/skills, two lanes (instruction-only vs code-backed), owners per area, pilot with 2-3 teammates.
- Open: how BMAD-built agents ship portably (they depend on station servers / per-tool agent formats differ).

## Ideate

ideation_methods: Analogous Inspiration, Brainstorming, SCAMPER Design, Provotype Sketching

### Analogous inspiration
- conda-forge staged-recipes -> feedstock: PR to a staging repo, lint bot, review, listing gets named maintainers, bots open version bumps. -> "staged-skills" contribution flow.
- Homebrew taps: any git repo can be a tap. -> station/team repos as federated sources aggregated by the marketplace index.
- VS Code marketplace: categories, install counts, verified publisher. -> badges and trust tiers.
- npm/PyPI: scoped names, semver, run without install. -> @station/skill names, versions, a `try` command.
- Hugging Face Hub: model cards with "use this" snippets per library. -> skill cards with per-tool install tabs.
- Artifactory remote repos: proxy of upstream. -> one build, two install sources (GitHub release asset, Artifactory package).

### Brainstorm (raw)
1. One generated index (marketplace.yaml/json) from all skill/agent folders drives Pages and every per-tool manifest.
2. One CLI (extend `steward catalog` or a new `bmad-mp`): search, info, install, update, outdated, uninstall, new, publish.
3. install writes to .agents/skills + .claude/skills, plus per-tool agent files where formats are known.
4. Agents ship as an agent skill (persona SKILL.md) plus generated per-tool adapters.
5. Agents declare `requires:` (station server, CLI, _bmad/ folder); installer checks and explains.
6. Skill card page per listing: what it does, readable steps, per-tool install tabs, owners, version, trust tier, last verified.
7. `new` scaffolds via bmad-builder (agent, skill, module).
8. `publish` opens a PR to the marketplace repo (staged-recipes style).
9. Lint bot: frontmatter, no absolute/repo paths, no secrets, license, size.
10. Clean-machine CI per listing (container), headless smoke test where a tool supports it.
11. Tag -> GitHub release zip + conda/pip package pushed to Artifactory from the same build.
12. Federated sources: station repos own their skills; index aggregates.
13. Bundles: "Python env + packaging starter", "new hire pack", per-station packs.
14. Task-based search and tag taxonomy ("lock an env", "scan deps").
15. Usage from Artifactory/GitHub download counts, no telemetry.
16. "Request a skill" issue form and wishlist board.
17. `outdated` / update notices.
18. Checksums / signed releases; verified publisher.
19. Trust tiers: bmad-certified (upstream), estate-reviewed, community.
20. Per-project skills.lock for reproducible skill sets.
21. MCP server so AI tools can search and install skills themselves.
22. Clean uninstall.
23. Contributor guide + template repo.

### SCAMPER over v1
- Substitute: Claude marketplace.json as core -> tool-neutral index; heavy steward gate -> PR review + CODEOWNERS.
- Combine: catalog.py engine + bmad-builder -> one create/publish CLI; browse.yaml + Pages -> generated site.
- Adapt: existing conda skill-bundle recipe pattern -> also install to .agents/skills.
- Modify: estate.yaml schema -> add agents, adapters, owners, trust tier, requires.
- Put to other uses: steward review records -> "reviewed by" on skill cards.
- Eliminate: extra ship backends, Frames, skillsctl slot, product C.
- Reverse: contributors self-publish into community tier; review promotes to verified.

### Provotypes
- No website at all; AI tools find and install via MCP mid-conversation. -> in-tool discovery matters.
- Every repeated chat question auto-drafts a skill PR. -> "skillify this session" capture command.
- Bots publish skills. -> same lint/review path for bot PRs.
- Skills expire unless CI passes regularly. -> freshness badge, auto-deprecate.
- Zero install: run a skill straight from a URL. -> `try` command.

### Concept clusters
A. Index + CLI for find/install/update, dual source (GitHub release or Artifactory).
B. Staged-skills contribution flow: new -> publish PR -> lint + CI -> review -> listed with owners and trust tier.
C. Skill cards on Pages: readable steps, per-tool install tabs, badges.
D. Portable agents: agent-as-skill + generated per-tool adapters + requires checks.
E. In-tool discovery and capture: MCP search/install, "skillify this session".
F. Trust and freshness: tiers, verified badge, CI freshness, checksums.

### Top concepts (selected by rxm7706): ALL of A-F
A find+install CLI, B PR contribution flow, C skill cards on Pages, D portable agents, E in-tool discovery + capture, F trust + freshness.
Approach: one thin end-to-end slice touching every concept rather than six separate prototypes.

## Prototype

prototype_approach: Storyboarding (end-to-end journey) + Paper Prototyping (CLI transcript, index entry, skill card mock) + Wizard of Oz (pilot with rxm7706 performing review/CI steps by hand before automating).

### Storyboard (one teammate, one loop)
1. Find (C, E): Dana (teammate, uses Cursor) asks her AI "how do we lock our env?"; the marketplace search (MCP or CLI) suggests @mason/environment; she opens its skill card on Pages: what it does, readable steps, Cursor install tab, owner, estate-reviewed badge, last verified date (F).
2. Install (A): `mp install @mason/environment` (from GitHub release or Artifactory). Files land in .agents/skills and .claude/skills; project skills.lock updated.
3. Use: Cursor picks up the skill; it locks her mixed conda+pip env.
4. Agent (D): she installs @scribe/agent; installer reports its requires (station server optional / missing) and installs agent-as-skill plus a Cursor adapter.
5. Capture (E): after solving an Artifactory auth quirk, she runs "turn this session into a skill"; `mp new` scaffolds via bmad-builder with her steps.
6. Publish (B): `mp publish` opens a PR to the marketplace repo; lint bot + clean-machine CI run; CODEOWNER reviews; merged into community tier, promoted to estate-reviewed.
7. Freshness (F): a scheduled CI run re-verifies listings; a broken one loses its verified badge and owners get an issue.
Success moment: a second teammate installs Dana's skill.

### Paper prototypes to make
- P1 CLI transcript: search, info, install, outdated, new, publish.
- P2 Index entry schema (one skill, one agent): name, kind, version, owners, tier, requires, adapters, sources (github, artifactory), verified_at.
- P3 Skill card mock (static HTML) for @mason/environment.
- P4 Wizard-of-Oz pilot: rxm7706 hand-performs review/CI/promote for 2-3 teammates' first skills.

### Paper prototypes (2026-10-20)
Files in `/workspace/dt/prototypes/` (sample data, not in the repo):
- `p1-cli-transcript.md`: mock terminal session for the `bmp` CLI (source config, search, info, install from GitHub release or Artifactory, skills.lock, agent install with requires checks and adapters, outdated/update, uninstall, new via bmad-builder, skillify, publish with lint + CI). Name decision: standalone `bmp`; it shares the `catalog.py` engine with `steward catalog`, which stays the maintainer/CI face.
- `p2-index-schema.yaml` + `p2-index-schema.md`: listing format, a superset of the upstream registry schema (v1 `estate.yaml`). Samples: `@mason/environment` skill, `@scribe/agent` agent with requires + adapters, `@bmad/creative-intelligence-suite` module. Per-tool manifests are generated from the index.
- `p3-skill-card.html` + `p3-skill-card.png`: static Pages skill card for `@mason/environment` (steps, per-tool install tabs, Artifactory/GitHub sources, badges, owners, requires, related, contribute links).
- `p4-wizard-of-oz-pilot.md`: manual pilot with 2–3 teammates; rxm7706 performs review, CI and promotion by hand.

features_to_test:
1. Task-based find (search + Pages index) vs in-tool discovery
2. One install command; dual source (GitHub release vs Artifactory)
3. Plain SKILL.md in `.agents/skills` + `.claude/skills` picked up by each teammate's tool
4. Readable steps for no-AI teammates
5. Trust signals: owner, tier, review record, verified date, CI status
6. Agent install: requires checks, CLI-only degraded mode, generated adapters
7. Contribution path: new / skillify → PR → lint + clean-machine check → review → promotion
8. skills.lock + outdated/update

## Test

### testing_plan
Two rounds, cheapest first:
- **Round 0, desk test (rxm7706 alone, before involving anyone):** on a clean machine or container, install the three rewritten seed skills by the manual script into `.agents/skills` + `.claude/skills`, and confirm each of Claude Code, Cursor, Copilot, Gemini CLI, Codex (and Devin if accessible) picks them up unmodified. Tests riskiest assumption #2 and catches repo-path leaks. Also run the manual lint + fresh-container checks once to size the CI work.
- **Round 1, Wizard-of-Oz pilot (P4):** 2-3 teammates (T1 Cursor + conda/pip, T2 Copilot or Gemini + publishes packages, T3 no AI tool or new hire). Tasks: find, judge trust, install, use on a real task, contribute one skill, second-user install. Real: skill content, internal GitHub repo, static Pages cards, one Artifactory package, real PRs. Faked: bmp install, search, CI, promotion, skillify, update notices.
- Capture: feedback grid (likes / questions / ideas / changes) per teammate per task, plus completed y/n, stuck point, tool, source, operator interventions.
- Riskiest assumptions: see P4 (8 listed); top 3 = teammates want skills in their AI tool at all; plain skill folders work unmodified in each tool; someone other than rxm7706 contributes.

### user_feedback
Pending: no pilot has run yet. Fill from the grids after Round 0 and Round 1.

### key_learnings
Pending pilot. Decision rules are pre-registered in P4 exit criteria (what to automate and when; stop/rethink if no teammate uses a seed skill on a real task or nobody contributes after being asked).

## Plan next iteration

### refinements (before the pilot)
1. Rewrite the three seed skills (@mason/environment, @warden/scan, @mason/package) off `pixi run -e` and repo paths; add a steps.md to each; verify real commands (prototype card commands are sample data).
2. Create the marketplace repo on internal GitHub (`skills/<scope>/<slug>/` + listing.yaml in the P2 schema) and a static Pages index + three cards from P3.
3. Publish one listing to Artifactory; the others as GitHub release zips.
4. Write the manual install script, a SKILL.md template, a PR template, and the manual check list (frontmatter, no repo paths, gitleaks, fresh-container install).
5. Confirm `bmp` doesn't collide with an existing internal tool name.

### action_items (sequence)
1. Round 0 desk test (rxm7706).
2. Fix what Round 0 breaks.
3. Recruit 2-3 pilot teammates matching T1-T3; send one launch message.
4. Run Round 1; fill grids; count operator interventions.
5. Apply P4 exit criteria to decide what to automate.
6. Hand off to BMAD planning: `bmad-product-brief` -> `bmad-prd` -> `bmad-architecture` -> `bmad-create-epics-and-stories` -> `bmad-sprint-planning` (or the usual `bmad-spec` route), with v1 Epic 60 code reused per the reset brief.

### success_metrics
- Primary: a teammate installs and uses a skill that a different teammate (not rxm7706) contributed.
- Each pilot teammate completes find -> install -> use on a real task.
- The T3 (no AI tool) teammate completes a task from steps alone.
- At least one merged contribution from someone other than rxm7706.
- Plain skill folders work unmodified in every pilot tool (or the gap is identified per tool).
- Operator interventions per task trend down; the most frequent manual step is the first thing automated.
