# BMAD Skills & Agents Marketplace — Dream Reset Brief (for a CIS session)

Prepared 2026-10-20 from `rxm7706/local-recipes` @ `53aed16fe` (main, 2026-10-19 05:49 CDT).
Goal of the session: **revisit the 2026-09-15 decisions and converge on a shippable, usable product** —
someone can *discover, install, and use* a listed skill or agent end to end.

Sources cited below (all repo-relative):
- Dream: `docs/dreams/self-hosted-bmad-marketplace.md` ("Dream")
- Spec folder: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-self-hosted-bmad-marketplace/` (`SPEC.md`, `backends-and-sources.md`, `.memlog.md`)
- Epic 60: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` §Epic 60
- Ledger: `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`
- Code: `src/shared/packages/pyforge-steward/catalog/`, `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py`, `recipes/pyforge-estate-catalog/`, `docs/foundry/frames/browse.yaml`

---

## (a) Problem framing (does not presuppose v1's answer)

rxm7706's estate has authored a lot of BMAD-shaped work — station agents (`bmad-agent-atlas`, `-doctor`, `-herald`,
`-marshal`, `-mason`, `-scribe`, `-steward`, `-warden`), `pyforge-*` and `mason-*` skills, SKF-forged skills, and
Frames — plus it wields official BMAD modules. Today that work is usable only inside this one repo's `.claude/skills/`.
The problem to solve: **someone who is not already sitting in this repo cannot find these skills/agents, judge
whether to trust them, get them installed into their own tool (Claude Code, Codex, or a BMAD project), and start
using them.** Who that "someone" is, what they come for, and which channel reaches them are open — that is what
this session decides.

## (b) What v1 built, and what the evidence shows

v1 = steward Epic 60, stories 60.1–60.4, all `done` (merged 2026-09-19 and 2026-10-08). Facts, not judgements:

| Evidence | Where |
|---|---|
| Config with plugin sources/backends exists; git is the edit store; `dedicated_repo: null` | `catalog/catalog.yaml` |
| Estate listings file is **empty**: `modules: []` ("v1 ships with no community modules (operator ruling 4)") | `catalog/registry/estate.yaml` |
| Claude manifest lists **4 rows, all official upstream BMAD modules** (TEA, builder, CIS, utility-skills), each a `github` pointer back to bmad-code-org | `catalog/.claude-plugin/marketplace.json` |
| Codex manifest has **zero plugins** | `catalog/.agents/plugins/marketplace.json` |
| Only review record is an example file | `catalog/registry/reviews/` |
| `bmad-method install --custom-source <catalog>` → **"Found 0 modules"**; installer does not follow `github` pointers. Verified 2026-09-19, re-verified "STANDS" 2026-10-01, status `open` | Ledger DW-FU-60-1-4 |
| Generated manifest drifts on recipe-only PRs; CI doesn't trigger render — status `open` | Ledger DW-FU-60-1 |
| Recommended follow-up review of 60.1 never ran — status `open` | Ledger DW-FRR-60-1 |
| "Browse" is a generated YAML file, not a page; every Frame row is `trust_tier: unverified` | `docs/foundry/frames/browse.yaml` |
| No dedicated GitHub catalog repo → the `github` marketplace-pointer form (Claude `extraKnownMarketplaces` / `codex plugin marketplace add owner/repo`) is not available; only `directory`/`--custom-source` forms are printed | `catalog.yaml` comment; `catalog.py` `pointers()` |
| No catalog commits after 2026-10-08 | git log |
| None of the estate's own agents/skills is listed anywhere | `estate.yaml`, manifests |
| Not verified here: whether `pyforge-estate-catalog` was actually published to the SelfExplainML channel | — |

Plain reading: **the plumbing works; there is nothing ours on the shelf, and the one install path we own returns zero.**

## (c) Decision review — the centre of the session

Q1–Q7 are quoted from Dream §"Open questions for the Spec" and §"Operator rulings (accepted 2026-09-15)".
"Rationale" is what the Dream/memlog states; where none is stated, it says so.

| # | Original question | Answer chosen (2026-09-15) | Stated rationale | What v1 evidence says now | Alternatives to reconsider |
|---|---|---|---|---|---|
| Q1 | "v1 SKU — A only, or A plus a consumed skillsctl face (B)?" | "v1 is our BMAD catalog plus estate Frames on the same rails. Not the Claude-skill store." B = empty source slot. | Dream: "v1 default candidate … SKU A only. B is a later face." Constraint: don't operate skillsctl's SQLite as "a fourth infra kind". | Most estate assets users would want are **Claude Code skills/agents**, which is SKU B's artifact — and none are listed. A-only shelf holds 4 upstream modules. | Lead with Claude Code/Codex **plugins** of our own skills & agents (B's artifact via the native plugin-marketplace format, no skillsctl server); or merge A+B into one listing type. |
| Q2 | "Browse UI in v1 — git + `extraKnownMarketplaces` is enough, or a hosted browse/install surface?" | "A thin browse list in v1 … Not a click-to-install App Store … Install still uses `bmad-method install` / pixi." | Avoid rebuilding MyBMAD / Collab / nebari-frames (Dream constraints). | Browse = a YAML file; install via `bmad-method install` returns 0 modules. Nobody can discover-then-install today. | A static GitHub Pages catalog page (Pages already exists for the repo); or rely on Claude Code's own `/plugin` browse UI and skip building one. |
| Q3 | "Registry home — internal git, object storage, conda channel, or a switchable set?" | "Git is where listings are edited. Shipping is a config switch." Default ship: pixi/conda package on SelfExplainML/Artifactory; object storage + bundle as plugins. | Air-gap: "Air-gap cannot depend on github.com plus Claude's public marketplace." | Three backends built; the channel tools (Claude/Codex) actually resolve marketplaces from a **git repo**, which v1 doesn't have (`dedicated_repo: null`). Air-gap user not yet named. | Public GitHub marketplace repo as the primary channel; conda/air-gap as a later backend only if a real air-gapped user exists. |
| Q4 | "Fork vs mirror of `bmad-plugins-marketplace` — carry their public index or start empty?" | "Our repo, their file format. Not an automatic mirror. Start with no community modules." Public catalog = source plugin, default off. | Don't blind-mirror; "three modules" count was stale. | Shelf has zero estate listings; re-listing upstream modules adds nothing users can't get upstream. | Start with **our own** 3–8 assets as the launch shelf; or contribute listings *to* upstream `bmad-plugins-marketplace` instead of hosting a parallel one. |
| Q5 | "Trust review — who reviews our listings, reuse their tiers or write our own?" | "Steward reviews our list. Reuse their tier names: Unverified / Community Reviewed / BMad Certified." | Keep our own review; their team doesn't review us. | No review has happened (only an example record). All Frames `unverified`. Gate exists with nothing to gate. | Lightweight gate (validator + one human check) sized to the first user; drop "BMad Certified" for estate-authored items to avoid implying upstream endorsement. |
| Q6 | "Billing — non-goal for v1, or a named later-cap?" | "No billing on this Spec." | None stated beyond deferring SKU C. | No evidence against. | Keep as non-goal unless the first user is external and paying. |
| Q7 | "Layer 3 / Frames — hoist the whitepaper marketplace, or only estate Frame list/share/add?" | "No Layer 3. Frame list / share / add-as-a-reviewed-git-listing is in." | Layer 3 is "still thesis" upstream. | Frames listed (8) but unverified; no evidence anyone outside consumes Frames. | Drop Frames from v-next entirely; focus on skills/agents the user asked about. |

Other recorded decisions worth a yes/no in the session (from `.memlog.md` and Dream §Constraints):

| Decision | Source | Reconsider? |
|---|---|---|
| Owner is **steward**; "A-only — not a foundry-product Dream for B" | `.memlog.md` 2026-09-14 decision | Should a marketplace of agents/skills be its own product rather than a steward duty? |
| "Three SKUs must stay distinct … Mixing them is how Hub LC-3 got bundled" | Dream §Three SKUs; `.memlog.md` | Is A vs B a real distinction for users, or only for us? |
| "Do not operate skillsctl or nebari-frames SQLite as a fourth infra kind" | `.memlog.md` constraint | Still valid if v-next is a static git marketplace (no server). |
| "Scribe: no plugin packaging until a second consumer repo" | Dream §What is real | Is there now a second consumer? If not, who is the first external user? |
| "Creating a new GitHub repo for the catalog still needs operator confirm" | Dream rulings; Epic 60 preamble | Decide it in this session. |
| Public BMAD catalog "cited, never a blind mirror" | `backends-and-sources.md` | Keep. |

## (d) Key open questions

1. **Who is the first user?** Only rxm7706 across his own machines/repos? His teams? Public BMAD users? Name one person.
2. **What job do they hire it for?** "Set up a new repo with my station agents in 2 minutes"? "Find a conda-forge packaging skill"? "Share my agents with a teammate"?
3. **What's on the shelf?** Skills vs agents vs full BMAD modules vs Frames — which unit does the first user install?
4. **Which channel reaches them?** Claude Code plugin marketplace (git repo), Codex marketplace, `bmad-method install --custom-source`, conda/pixi, or plain git.
5. **Curation/trust:** what's the minimum review that makes a listing trustworthy to *that* user?
6. **A/B/C:** merge A+B into one "plugin" listing? Keep C killed?
7. **"Shippable" in 2–4 weeks:** what single end-to-end path must work on a clean machine?

## (e) Recommended session sequence (real skill names, from `.claude/skills/`)

How to invoke in Claude Code from the repo root: call the skill by name (e.g. `/bmad-cis-design-thinking`) or use
its trigger phrase from its `SKILL.md`. CIS agents are personas whose menus call the workflows:
`bmad-cis-agent-design-thinking-coach` (Maya, `DT` → `bmad-cis-design-thinking`),
`bmad-cis-agent-brainstorming-coach` (Carson, `BS` → core `bmad-brainstorming`),
`bmad-cis-agent-creative-problem-solver` (Dr. Quinn, `PS` → `bmad-cis-problem-solving`),
`bmad-cis-agent-innovation-strategist` (Victor, `IS` → `bmad-cis-innovation-strategy`),
`bmad-cis-agent-storyteller` (Sophia → `bmad-cis-storytelling`),
`bmad-cis-agent-presentation-master` (Caravaggio, slides). Note: CIS 0.3.2 has no brainstorming workflow of its own;
Carson uses core `bmad-brainstorming`.

| Step | Skill | Feed it | Expected output |
|---|---|---|---|
| 1. Empathize & define | `bmad-cis-design-thinking` ("lets run design thinking") | §(a), §(b), §(d) Q1–Q3 | **Named first user + job-to-be-done**, POV statement, 3–5 "How might we…" |
| 2. Diverge | `bmad-brainstorming` (or Carson `BS`) | Step-1 HMWs + §(c) "Alternatives" column | Long list of product shapes, shelf contents, channels, incl. A+B merge |
| 3. Diagnose v1 | `bmad-cis-problem-solving` ("guide me through structured problem solving") | §(b) evidence table, DW-FU-60-1-4 | Root causes of "empty shelf / 0 installs"; which Q1–Q7 answers caused them |
| 4. Position | `bmad-cis-innovation-strategy` ("lets create an innovation strategy") | Steps 1–3 + upstream landscape in Dream §What is real | Where we add value vs upstream `bmad-plugins-marketplace` / Claude plugin marketplaces; **kill criteria** |
| 5. Re-decide | `bmad-party-mode` (CIS agents + `bmad-agent-pm` + `bmad-agent-architect`), then `bmad-advanced-elicitation` (pre-mortem / red team) | §(c) decision table | **Re-decided decision table**: each Q1–Q7 + other decisions → keep / change / drop, with new rationale |
| 6. Converge | `bmad-prfaq` ("work backwards") — or `bmad-cis-storytelling` for the narrative | Steps 1–5 | **Product statement** + press release + FAQ that the first user would believe |
| 7. Lock scope | `bmad-product-brief` | PRFAQ + decision table | Brief with: first user, JTBD, **v-next scope**, **acceptance criteria**, non-goals, kill criteria |

**Build-ready exit criteria for the session** (all seven must exist before handoff):
re-decided decision table · named first user + JTBD · one-line product statement · v-next scope ·
acceptance criteria · kill criteria · list of launch-shelf items.

Starter acceptance criteria to test/replace in step 7 (candidate, not decided):
1. On a clean machine, the first user adds the marketplace with one documented command and sees ≥3 estate-authored listings.
2. They install one listed agent/skill with one command and invoke it successfully in a fresh project.
3. Each listing shows source, trust tier, version, and install line; a validator gate runs in CI.
4. Manifest drift fails CI (closes DW-FU-60-1); the BMAD-installer path either installs ≥1 module or is explicitly dropped (closes DW-FU-60-1-4).

Kill criteria to start from: no named user outside the estate after step 1; or upstream already serves the JTBD with a PR-to-their-registry.

**Handoff into planning** (real skills present): `bmad-product-brief` → `bmad-prd` → `bmad-ux` (only if a browse page is in scope) →
`bmad-architecture` → `bmad-create-epics-and-stories` → `bmad-sprint-planning` → `bmad-build`.
Estate convention is Dream → `bmad-spec` → steward epic; pick one route at step 7 and record it as a re-decided decision,
then update/supersede `docs/dreams/self-hosted-bmad-marketplace.md` and the Epic 60 retro (`bmad-retrospective`, currently `optional`).

## (f) Reuse vs throw away (v1 inventory)

| Item | Verdict | Why |
|---|---|---|
| `catalog.py` source/backend plugin registries, `check/render/list/publish/ship` verbs (+1523-line tests) | **Reuse** | Format-agnostic engine; new channel = new plugin |
| `.claude-plugin/marketplace.json` + `.agents/plugins/marketplace.json` renderers | **Reuse** | Already the native Claude/Codex marketplace formats |
| `registry/estate.yaml` (upstream schema) + `registry/reviews/` gate | **Reuse** | Just needs real listings |
| `wielded-suite` source (4 upstream modules) | Reconsider | Adds little for users; keep only if the first user needs a one-stop list |
| `recipes/pyforge-estate-catalog` conda backend | Park | Keep if an air-gapped user is named; otherwise off |
| Object-storage / git-bundle backends | Park | No user yet |
| `browse.yaml` / `frame-index.yaml` | Reuse as data, not as UI | Could feed a Pages page |
| Estate Frames source | Drop from v-next unless step 1 names a Frames user | No consumer evidence |
| `claude-skill-registry` empty slot (skillsctl) | Drop or keep empty | Native plugin marketplaces may cover it with no server |
| `bmad-method install --custom-source` path | Fix or drop | Returns 0 modules today (DW-FU-60-1-4) |
