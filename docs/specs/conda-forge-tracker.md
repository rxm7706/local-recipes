# Tech Spec: `conda-forge-tracker`

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bounded scope, single-user feature, ~13 implementation stories).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/conda-forge-tracker.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Target users | Solo conda-forge maintainer (initially rxm7706); pattern reusable for any individual maintainer |
| Distribution | Local-only directory; no PyPI / conda / pip package |
| Lifetime | Long-running — replaces ad-hoc personal tracking of conda-forge involvement |
| Sibling to | `local-recipes/` (this repo) |

---

## Background and Context

### The problem

The owner maintains, co-maintains, consumes, or has requested numerous
conda-forge packages across many feedstocks. Without a tracker:

- Upstream releases drift past while autotick PRs go stale.
- Package requests (things wanted on conda-forge but not yet there) get
  forgotten between sessions.
- Build failures on platform variants (linux-aarch64, osx-arm64) get
  lost in GitHub notifications.
- Stuck PRs and rerender requests pile up without follow-through.
- Mark-broken / yank actions are manual one-offs with no record.

### What's been ruled out

- **Direct GitHub Issues.** Requires online access for every interaction;
  not air-gap-friendly per `docs/enterprise-deployment.md` philosophy.
  Migration *to* GitHub Issues remains a deliberate future option.
- **Existing community tools.** Survey of `conda-forge/`, `regro/`,
  `prefix-dev/`, and `conda-incubator/` orgs found no personal-tracker
  tool. This is genuinely blue-sky territory.
- **`conda-forge.org/maintainers/<user>` URL.** Does not exist; no
  scrapeable maintainer dashboard.
- **`conda-forge-metadata` Python API as primary data source.** Surface
  unverified at spec-time; defer until the API is inspected directly.

### What's available to leverage

- **`conda-forge-expert` skill** (`local-recipes/.claude/skills/conda-forge-expert/`)
  already provides `update_recipe`, `update_recipe_from_github`,
  `check_github_version`, `scan_for_vulnerabilities`,
  `analyze_build_failure`. The tracker reuses these via a bridge — does
  not duplicate.
- **`regro/cf-graph-countyfair`** has `node_attrs/<package>.json` files
  containing `meta_yaml.extra.recipe-maintainers`. Cloned once locally,
  this enables discovery without 28k GitHub API calls.
- **`prefix-dev/parselmouth`** exposes a stable JSON URL pattern
  (`https://conda-mapping.prefix.dev/pypi-to-conda-v1/{channel}/{pkg}.json`)
  for "is package X on conda-forge?" checks.
- **CLAUDE.md `## Conda-Forge Ecosystem Reference`** is the authoritative
  map of every repo and doc the tracker may need to surface to the user.

---

## Goals

- **G1.** Single source of truth (`tracker.yaml`) for packages the owner
  is involved with as `maintainer`, `co-maintainer`, `consumer`, `client`,
  or `requestor`.
- **G2.** Automated detection of outdated upstreams (`audit.py`) that
  files idempotent markdown issues — no duplicates for the same target
  version.
- **G3.** Markdown-first issue capture with frontmatter that maps 1:1
  to GitHub Issue fields, so a future migration is a single script run.
- **G4.** Reuse `conda-forge-expert` skill scripts via a thin bridge.
  No code duplication.
- **G5.** Air-gap-friendly: after the initial sync, all reads/writes
  are local. Network is required only for `sync.py` and outbound version
  checks in `audit.py`.
- **G6.** Discoverability — `sync.py --discover` clones cf-graph once
  and finds every feedstock where the owner is a recipe-maintainer.
- **G7.** Channel-aware: each issue has a `channel` field that maps to
  one of five upstream destinations (local, feedstock-issue,
  feedstock-comment, admin-request, staged-recipes).

## Non-Goals

- **NG1.** No GitHub Issues at start. Markdown-first; export is on demand.
- **NG2.** No automated upstream PR creation. The autotick bot
  (`regro-cf-autotick-bot`) and `webservices` already do this.
- **NG3.** No build/test of mirrored feedstocks. Mirrors are read-only
  references to the recipe state.
- **NG4.** No web UI / TUI. Markdown grep is enough for these volumes.
- **NG5.** No external notifications (email, Slack, Discord). Stdout only.
- **NG6.** No multi-user / team-shared deployment. One owner, one machine.
- **NG7.** No reimplementation of `conda-forge-expert` skill scripts.
  Bridge or fail.
- **NG8.** No CVE auto-audit in v1 (deferred to v2 — `scan_for_vulnerabilities`
  exists in the skill; tracker integration is a follow-up).

---

## Lifecycle Expectations

The tracker is **long-running**, unlike the transitional copilot-bridge:

- **Bootstrap** once: scaffold the directory, populate `tracker.yaml`
  (manually or via `--discover`), run initial `sync.py`.
- **Use weekly** (typical cadence): `sync.py && audit.py` to refresh
  mirrors and surface new outdated packages. Manually file follow-up
  issues via `new-issue.py` as situations arise.
- **Migrate to GitHub Issues** *when/if needed*: run
  `export-to-github.py` against a target repo; markdown stays
  authoritative until the next migration if the user reverts.
- **Never decommission**. Personal tracking is permanent.

---

## User Stories

Each story is sized for one BMAD `bmad-create-story` /
`bmad-dev-story` cycle.

### Story 1 — Scaffold directory + git init
**As** the owner,
**I want** a sibling directory `~/UserLocal/Projects/Github/rxm7706/conda-forge-tracker/`
with the canonical layout, gitignore, and a local-only git repo,
**so that** I have a versioned home for the tracker without exposing
it on GitHub.

**Acceptance:**
- Directory created with subdirs `mirrors/`, `issues/`, `templates/`,
  `scripts/`.
- `.gitignore` excludes `mirrors/`, `tracker.discovered.yaml`,
  `__pycache__/`, IDE folders.
- `git init` (no remote).
- README.md documents purpose, layout, schemas, channels, workflows.
- `tracker.yaml` exists with `packages: []` and a top-of-file comment
  documenting the schema.

### Story 2 — `_common.py` shared utilities
**As** a script author,
**I want** a single module exposing frontmatter parsing, ID assignment,
slug generation, paths, and channel/role/status enums,
**so that** every script in the tracker shares one source of truth.

**Acceptance:**
- Exposes `Issue` dataclass, `parse_issue`, `list_issues(state=None)`,
  `next_issue_id`, `slugify(text)`, `write_issue(fm, body)`,
  `load_tracker`, `today`.
- Exposes module-level `CHANNELS`, `ROLES`, `STATUSES` sets.
- Module-level path constants: `ROOT`, `ISSUES_DIR`, `TEMPLATES_DIR`,
  `MIRRORS_DIR`, `TRACKER_FILE`, `DISCOVERED_FILE`.
- Frontmatter regex handles malformed files gracefully (warns, skips).

### Story 3 — Issue templates: `package-request`, `outdated-package`, `stuck-pr`
**As** the owner,
**I want** three core templates with `{{placeholder}}` fields and
GitHub-Issue-compatible frontmatter,
**so that** `new-issue.py` can substitute fields and write a valid
issue.

**Acceptance:**
- Each template has frontmatter with: `id` (placeholder), `title`,
  `state: open`, `channel`, `labels`, `assignees: [rxm7706]`,
  `created_at: {{date}}`, `closed_at: null`, `gh_issue_number: null`,
  plus template-specific fields (`feedstock`, `upstream`, version
  pair, etc.).
- Body has a `## Action` checklist and a `## References` footer
  linking the relevant CLAUDE.md ecosystem row + Zulip + Knowledge
  Base where applicable.
- `package-request.md` channel = `staged-recipes`.
- `outdated-package.md` channel = `feedstock-issue`.
- `stuck-pr.md` channel = `local`.

### Story 4 — Issue templates: `build-failure`, `rerender-request`, `mark-broken-yank`
**As** the owner,
**I want** three more templates covering common feedstock-maintainer
actions,
**so that** I can capture build failures, rerender needs, and yank
requests with no manual frontmatter.

**Acceptance:**
- `build-failure.md` channel = `feedstock-issue`; body links the
  skill's `analyze_build_failure` tool and Knowledge Base.
- `rerender-request.md` channel = `feedstock-comment`; body is the
  literal `@conda-forge-admin please rerender` text.
- `mark-broken-yank.md` channel = `admin-request`; body is the
  literal YAML payload that goes into a `conda-forge/admin-requests`
  PR (paste-ready).

### Story 5 — `new-issue.py` CLI
**As** the owner,
**I want** a CLI to scaffold a new issue from a template with
substituted fields,
**so that** I never hand-author frontmatter.

**Acceptance:**
- Signature: `new-issue.py <template> --field key=value [--field …]`.
- Auto-assigns next `id`.
- Always sets `created_at` to today.
- Replaces `{{key}}` placeholders; unfilled `{{X}}` becomes `TODO_X`.
- Validates `channel` against `_common.CHANNELS`; warns (does not
  fail) on unknown channels.
- Output: `created: issues/<id>-<slug>.md`.

### Story 6 — `sync.py` mirror clone/fetch
**As** the owner,
**I want** to refresh local shallow clones of every active feedstock
in `tracker.yaml`,
**so that** `audit.py` can read the recipe's current version.

**Acceptance:**
- For each entry where `feedstock` is set and `status` ≠ `requested`:
  - First run: `git clone --depth 1 https://github.com/conda-forge/<feedstock>.git mirrors/<feedstock>/`
  - Subsequent runs: `git fetch --depth 1 origin && git reset --hard origin/HEAD`
- `--depth N` overridable.
- `--dry-run` lists targets without cloning.
- Idempotent.

### Story 7 — `_cf_tools.py` bridge to `local-recipes`
**As** a tracker script author,
**I want** a single helper that adds the `conda-forge-expert` skill
scripts to `sys.path`,
**so that** I can `import update_recipe` etc. without duplicating code.

**Acceptance:**
- Default lookup: `../local-recipes` (sibling).
- Override: `$LOCAL_RECIPES_DIR` env var.
- Helpers: `get_local_recipes_dir()`, `get_skill_scripts_dir()`,
  `add_to_sys_path()`, `import_skill_module(name)`.
- Raises a clear `RuntimeError` with remediation when the skill
  scripts dir is not found.

### Story 8 — `audit.py` outdated-upstream check (active packages)
**As** the owner,
**I want** `audit.py` to compare each tracked feedstock's current
version against PyPI / GitHub releases and file an issue when behind,
**so that** I never miss a release that autotick didn't catch.

**Acceptance:**
- For `status: active` entries: read `mirrors/<feedstock>/recipe/recipe.yaml`
  (fall back to `meta.yaml`), parse `version`.
- Look up upstream latest:
  - GitHub releases if `upstream:` matches `github.com/<owner>/<repo>`
    (use `_cf_tools.import_skill_module('github_version_checker')`
    where possible; fall back to direct API call).
  - Otherwise PyPI via the package name.
- File a new `outdated-package` issue iff no open issue with the same
  fingerprint `(feedstock, label=outdated, target_version)` exists.
  Closed issues with the same fingerprint also block re-creation.
- `--dry-run` lists what would be filed.
- `--package <name>` filters to a single tracker entry.

### Story 9 — `audit.py` requested-now-on-cf check
**As** the owner,
**I want** `audit.py` to detect when a `requestor` package now exists
on conda-forge,
**so that** I'm prompted to update `tracker.yaml` from `requested` to
`active`.

**Acceptance:**
- For `status: requested` entries: HEAD-check
  `https://conda-mapping.prefix.dev/pypi-to-conda-v1/conda-forge/<name>.json`.
- On 200: file a `local`-channel issue ("Now on conda-forge: <name>")
  with body instructing the owner to update `tracker.yaml`.
- Idempotent — does not re-file when an open `request-fulfilled` issue
  already exists for that name.

### Story 10 — `sync.py --discover` via cf-graph
**As** the owner,
**I want** to find every conda-forge feedstock where I'm a recipe
maintainer without hand-curating,
**so that** my `tracker.yaml` becomes complete without manual GitHub
spelunking.

**Acceptance:**
- `python scripts/sync.py --discover` clones (or fetches)
  `regro/cf-graph-countyfair` into `mirrors/_cf-graph/` (depth 1).
- Iterates `mirrors/_cf-graph/node_attrs/*.json`, parsing
  `meta_yaml.extra.recipe-maintainers`.
- For each match (default user `rxm7706`, override
  `--maintainer <user>`): emit an entry to `tracker.discovered.yaml`
  with `role: maintainer` (single maintainer) or `co-maintainer`
  (multiple), `status: active`, `notes: "discovered from cf-graph at <date>"`.
- `tracker.discovered.yaml` is gitignored — it's a review surface, not
  a commit target. Manual merge into `tracker.yaml`.
- `--dry-run` skips clone and prints the planned action.
- Re-running rebuilds `tracker.discovered.yaml` from scratch.

### Story 11 — `export-to-github.py` skeleton
**As** the owner,
**I want** a stub script that documents the channel-routing plan for
migrating markdown issues to GitHub,
**so that** the schema is locked-in from day 1 and turning this on
later is a known-cost operation.

**Acceptance:**
- Script docstring documents: per-channel destination
  (local / feedstock-issue / feedstock-comment / admin-request /
  staged-recipes) and the `gh` CLI command shape for each.
- Implementation prints "not yet implemented; see docstring" and
  exits non-zero.
- Accepts `--repo` and `--dry-run` args (not yet wired).

### Story 12 — Smoke tests
**As** a future maintainer of the tracker (or an LLM agent),
**I want** smoke tests that verify the scripts import, the templates
parse, and `new-issue.py` round-trips,
**so that** drift is caught early.

**Acceptance:**
- `tests/test_smoke.py` imports every script (no execution).
- `tests/test_templates.py` validates each template has well-formed
  frontmatter and a known channel.
- `tests/test_new_issue.py` runs `new-issue.py outdated-package
  --field feedstock=test --field current=1 --field target=2` against
  a `tmp_path` and verifies file contents.
- Runs in `local-recipes`'s pixi env (no separate env required).

### Story 13 — README and migration playbook
**As** a future user,
**I want** a README that explains the workflow and a migration
playbook that documents the path from markdown to GitHub Issues,
**so that** I can pick this up cold months later without re-deriving
the design.

**Acceptance:**
- README sections: Purpose, Layout, Schemas (`tracker.yaml`,
  frontmatter), Channels, Workflows (table of common situations →
  command), Bridge to `local-recipes`, Migration to GitHub Issues.
- Migration playbook embedded in `export-to-github.py` docstring.
- README cross-links the CLAUDE.md ecosystem reference and the
  conda-forge-expert SKILL.md.

---

## Functional Requirements

### FR-1: Air-gap-friendly post-bootstrap
After the initial `sync.py` clone, all `audit.py` / `new-issue.py`
operations except the actual upstream version check MUST work without
network access. Reading mirrors, filing issues, listing issues — all
local.

### FR-2: Idempotent audit
`audit.py` MUST NOT file a duplicate issue for the same fingerprint:
`(feedstock, label, target_version)` for `outdated`,
`(feedstock, label)` for non-versioned issues. Open AND closed issues
with the same fingerprint block re-filing.

### FR-3: State in frontmatter
Issue state MUST live in YAML frontmatter (`state: open|closed`), not
in directory structure. Closed issues stay in `issues/`. No file moves.

### FR-4: Channel-aware migration
Every issue MUST have a `channel` field with value in:
`{local, feedstock-issue, feedstock-comment, admin-request, staged-recipes}`.
The migration script routes by channel.

### FR-5: Bridge over copy
Tracker scripts MUST NOT copy code from `local-recipes/.claude/skills/conda-forge-expert/scripts/`.
All cross-references go through `_cf_tools.py`. Override path with
`$LOCAL_RECIPES_DIR`.

### FR-6: Role-gated audit
| Role | Active checks (v1) | Watching (v1) |
|---|---|---|
| `maintainer`, `co-maintainer` | outdated upstream | dry-run only |
| `consumer`, `client` | outdated upstream | dry-run only |
| `requestor` | "now on conda-forge?" | n/a |

CVE / pinning / build-failure auto-checks are explicitly v2.

### FR-7: Discovery is opt-in
`sync.py --discover` is only triggered by the explicit flag. Default
`sync.py` only clones/fetches what's already in `tracker.yaml`.

### FR-8: Slug and ID conventions
- Issue ID: monotonic integer, zero-padded to 3 digits in the filename
  (`001-<slug>.md`).
- Slug: lowercase, hyphenated, max 60 chars.
- `created_at` / `closed_at`: ISO date (`YYYY-MM-DD`), no timestamp.

---

## Technical Approach

### Stack
- **Language:** Python 3.10+ (matches `local-recipes` pixi env floor).
- **Deps:** `pyyaml` (frontmatter + tracker.yaml). Stdlib `urllib`
  for HTTP — no `requests` dependency.
- **Test:** `pytest` (reuses `local-recipes` pixi env).
- **Build:** none — direct `python scripts/<name>.py`.

### File layout
```
~/UserLocal/Projects/Github/rxm7706/conda-forge-tracker/
├── README.md
├── .gitignore                      # mirrors/, tracker.discovered.yaml, __pycache__/
├── tracker.yaml                    # canonical, hand-curated
├── tracker.discovered.yaml         # GITIGNORED — auto-generated by sync.py --discover
├── mirrors/                        # GITIGNORED
│   ├── _cf-graph/                  # cf-graph-countyfair (for --discover)
│   └── <feedstock>/                # one per tracked feedstock
├── issues/<id>-<slug>.md           # state + channel in frontmatter
├── templates/
│   ├── package-request.md          # channel: staged-recipes
│   ├── outdated-package.md         # channel: feedstock-issue
│   ├── stuck-pr.md                 # channel: local
│   ├── build-failure.md            # channel: feedstock-issue
│   ├── rerender-request.md         # channel: feedstock-comment
│   └── mark-broken-yank.md         # channel: admin-request
├── scripts/
│   ├── _common.py                  # frontmatter, IDs, paths, enums
│   ├── _cf_tools.py                # bridge to local-recipes skill
│   ├── sync.py                     # clone/fetch mirrors; --discover
│   ├── audit.py                    # outdated check; requested-now-on-cf check
│   ├── new-issue.py                # CLI from template
│   └── export-to-github.py         # SKELETON — channel-aware migration
└── tests/
    ├── test_smoke.py
    ├── test_templates.py
    └── test_new_issue.py
```

### Schemas

#### `tracker.yaml`
```yaml
packages:
  - name: numpy                      # conda-forge package name
    feedstock: numpy-feedstock       # repo slug under conda-forge/
    role: co-maintainer              # see Roles
    status: active                   # see Statuses
    upstream: https://github.com/numpy/numpy
    notes: ""
```

**Roles**: `maintainer`, `co-maintainer`, `consumer`, `client`, `requestor`
**Status**: `active`, `watching`, `requested`

#### Issue frontmatter
```yaml
---
id: 001
title: "Outdated: numpy-feedstock 2.3.0 → 2.4.0"
state: open                          # open | closed
channel: feedstock-issue             # see Channels
labels: [outdated, autotick]
assignees: [rxm7706]
created_at: 2026-04-30
closed_at: null
feedstock: numpy-feedstock
upstream: https://github.com/numpy/numpy
current_version: "2.3.0"
target_version: "2.4.0"
gh_issue_number: null                # populated by export-to-github.py
---
```

### Channels (the routing model)

| `channel` value | Migrates to | Use cases |
|---|---|---|
| `local` | private todo / target tracker repo if pushed | Personal followups, watching list, drafts |
| `feedstock-issue` | issue on `conda-forge/<pkg>-feedstock` | Build failure, dep update, version bump |
| `feedstock-comment` | comment on a feedstock PR | `@conda-forge-admin rerender`, `restart ci`, `add user @x` |
| `admin-request` | PR to `conda-forge/admin-requests` | mark-broken, yank, archive, transfer, token reset |
| `staged-recipes` | PR to `conda-forge/staged-recipes` | New package request |

### Key decisions

1. **Markdown over JSON / SQLite.** Human-grep-able; one `gh issue create`
   call away from migrating to GitHub Issues. Volume (hundreds, not millions)
   makes a database overkill.
2. **State in frontmatter, not directory.** Single grep target; closing
   an issue mutates only its frontmatter — no file move, no broken
   inbound references.
3. **Idempotent fingerprint.** `audit.py` dedupes on `(feedstock, label,
   target_version)`. Closed-issue dedupe is by intent: "we already
   addressed this version, don't re-file". Future versions are not
   blocked.
4. **Channel field routes migration.** `export-to-github.py` is
   future-proof: it doesn't push everything to one repo, but each issue
   to its real upstream.
5. **Bridge over copy.** Tracker reuses skill scripts; future skill
   updates flow through. Drift detection: when a skill API changes,
   tracker tests fail.
6. **cf-graph local clone over GitHub API.** Discovery would otherwise
   need ~28k API calls. One clone is one HTTP transaction at the cost
   of disk space.
7. **Markdown-first, GitHub-Issues-eventually.** Frontmatter schema is
   GitHub-superset; no schema change at migration time.
8. **No own pixi env.** Tracker reuses `local-recipes`'s pixi env via
   the bridge; no `pixi.toml` of its own.

### Bridge mechanism

`scripts/_cf_tools.py`:

```python
DEFAULT_LOCAL_RECIPES = (
    Path(__file__).resolve().parent.parent.parent / "local-recipes"
)

def get_local_recipes_dir() -> Path:
    return Path(os.environ.get("LOCAL_RECIPES_DIR", str(DEFAULT_LOCAL_RECIPES)))

def get_skill_scripts_dir() -> Path:
    root = get_local_recipes_dir()
    scripts = root / ".claude" / "skills" / "conda-forge-expert" / "scripts"
    if not scripts.exists():
        raise RuntimeError(...)
    return scripts

def add_to_sys_path() -> None: ...
def import_skill_module(name: str): ...
```

Tracker scripts that need skill functions:
```python
import _cf_tools
gv = _cf_tools.import_skill_module("github_version_checker")
gv.check_github_version(...)
```

### Discovery algorithm (`sync.py --discover`)

```
1. git clone --depth 1 https://github.com/regro/cf-graph-countyfair mirrors/_cf-graph/
   (or git fetch + git reset --hard origin/HEAD if it exists)
2. all_feedstocks_path = mirrors/_cf-graph/all_feedstocks.json
   active = json.load(open(all_feedstocks_path))["active"]
3. found = []
   for name in active:
       node = mirrors/_cf-graph/node_attrs/{name}.json
       if not node.exists(): continue
       data = json.load(open(node))
       maintainers = data.get("meta_yaml", {}).get("extra", {}).get("recipe-maintainers", []) or []
       if MAINTAINER in maintainers:
           found.append({
               "name": name,
               "feedstock": f"{name}-feedstock",
               "role": "co-maintainer" if len(maintainers) > 1 else "maintainer",
               "status": "active",
               "notes": f"discovered from cf-graph at {today}"
           })
4. write found to tracker.discovered.yaml (sorted by name)
5. report: "review tracker.discovered.yaml; merge entries into tracker.yaml manually."
```

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Manually editing `tracker.yaml` to add one feedstock and
  running `python scripts/sync.py` produces `mirrors/<feedstock>/`
  with the recipe readable.
- **AC-2.** Running `python scripts/audit.py` against an
  intentionally-stale tracker entry files exactly one new
  `outdated-package` issue. Re-running the same command files zero.
- **AC-3.** Running `python scripts/new-issue.py outdated-package
  --field feedstock=foo --field current=1.0 --field target=1.1`
  produces a valid markdown issue with auto-assigned ID and today's
  date.
- **AC-4.** Running `python scripts/sync.py --discover` (with a fresh
  cf-graph clone) writes `tracker.discovered.yaml` listing every
  feedstock where `rxm7706` appears in `recipe-maintainers`.
- **AC-5.** All six templates parse as valid YAML+markdown and use a
  channel value in `_common.CHANNELS`.
- **AC-6.** All scripts import without raising (smoke test).
- **AC-7.** No tracker script copies code from
  `local-recipes/.claude/skills/conda-forge-expert/scripts/`. Cross-references
  go through `_cf_tools.py`.
- **AC-8.** Closed issues remain in `issues/` and continue to block
  duplicate filing (closed-issue dedupe).

---

## Open Questions

These are the design decisions captured during spec drafting. Each
has a recommended default; the BMAD planner agent should elicit
explicit answers before implementation.

### Must answer (v1-blocking)

| # | Question | Default |
|---|---|---|
| Q1 | Directory name | `conda-forge-tracker` |
| Q2 | Maintainer username — hardcode, `git config`, or env var? | hardcode `rxm7706` + optional `$CF_TRACKER_MAINTAINER` override |
| Q3 | Local `git init` (no remote)? | yes — versioned history of `tracker.yaml` and issues |
| Q4 | `tracker.discovered.yaml` — commit or gitignore? | gitignore — machine-generated, manual review then merge |
| Q5 | Closed issues — keep forever or archive after N months? | keep forever |
| Q6 | `audit.py` — auto-commit new issues, or leave in working tree? | leave in working tree |
| Q7 | Templates v1 set | 6: package-request, outdated-package, stuck-pr, build-failure, rerender-request, mark-broken-yank |
| Q8 | `mark-broken-yank.md` body | literal admin-requests YAML payload (paste-ready) |
| Q13 | Bridge default path to `local-recipes` | `../local-recipes`, override via `$LOCAL_RECIPES_DIR` |
| Q14 | `audit.py` calls into the skill (not reimplements) | yes — reuse `update_recipe`, `update_recipe_from_github`, `check_github_version` |

### Behavior — confirm or override

| # | Question | Default |
|---|---|---|
| Q9 | Role-gated audit checks (see FR-6 table) | as stated |
| Q10 | Auto-close issues when condition resolves vs. always manual? | manual close in v1 |
| Q11 | Reopen vs new issue when a closed condition recurs? | file new issue |
| Q12 | `audit.py --package <name>` filter for single-entry runs | yes |
| Q15 | `--discover` — set `co-maintainer` when multiple maintainers including me? | yes |
| Q16 | Discovery merge flow | manual review of `tracker.discovered.yaml` |
| Q17 | Re-running `--discover` when entries exist | rebuild `tracker.discovered.yaml` from scratch each run |

### Conventions

| # | Question | Default |
|---|---|---|
| Q18 | Issue ID width | 3 digits (`001`) |
| Q19 | Slug max length | 60 chars |
| Q20 | `created_at` format | ISO date (`2026-04-30`) |

### v2 — explicitly deferred

| # | Item | Why deferred |
|---|---|---|
| Q21 | CVE auto-audit via `scan_for_vulnerabilities` | Requires v1 to be running first; CVE workflow benefits from learning audit cadence |
| Q22 | Pinning-feedstock change tracking | Requires diff logic against pinning history; substantial scope |
| Q23 | Status dashboard scrape for active migrations | HTML-only endpoint; needs parser; zero migrations active at spec time anyway |
| Q24 | `/schedule`d weekly audit | Operational concern; v1 establishes the manual cadence first |
| Q25 | `export-to-github.py` real implementation | Skeleton in v1 locks the schema; full implementation when migration is actually wanted |

### Genuinely open (design call)

| # | Question | Tradeoff | Default |
|---|---|---|---|
| Q26 | Cross-link `local-recipes/recipes/<pkg>/` ↔ tracker (e.g., scaffolding a new recipe in `local-recipes/recipes/` auto-creates a `requestor` entry)? | Coupling helps you not forget to track requests; decoupling keeps the tracker portable to other recipe-staging repos. | Decoupled in v1; revisit if the owner finds themselves frequently forgetting to track new requests. |

---

## Dependencies and Constraints

- **D-1.** Requires `local-recipes/` checkout (default sibling location)
  for the bridge. `$LOCAL_RECIPES_DIR` overrides.
- **D-2.** Requires `git` for `sync.py`.
- **D-3.** Requires Python 3.10+ and PyYAML.
- **D-4.** Requires network on first sync (cf-graph clone, mirror
  clones, version-check API calls). After that, only audit's outbound
  checks need network.
- **D-5.** Anonymous GitHub API access is sufficient for version
  lookups (rate-limit 60/hr). With auth via `$GITHUB_TOKEN`,
  rate-limit jumps to 5000/hr.
- **C-1.** cf-graph-countyfair clone size is approximately 1–5 GB
  (single repo, deep history). `--depth 1` is acceptable for discovery
  since we only read `node_attrs/*.json` at HEAD.
- **C-2.** `parselmouth` URL pattern is the documented public surface;
  if it changes, the "now on conda-forge" check needs updating.
- **C-3.** Conda-forge feedstock naming follows the
  `<package>-feedstock` convention. Edge cases (e.g., scoped npm
  packages, rust crates with hyphens) follow CFEP-26 — derivable
  from the recipe but not from the package name alone.

---

## Out of Scope (Explicit)

- ❌ GitHub Issues from day 1.
- ❌ Automated upstream PR creation (autotick + webservices already
  cover this).
- ❌ Build / test of mirrored feedstocks.
- ❌ Web UI / TUI / dashboard.
- ❌ External notifications (email, Slack, Discord).
- ❌ Multi-user / team-shared tracking.
- ❌ Reimplementing `conda-forge-expert` skill scripts.
- ❌ CVE auto-audit (v2).
- ❌ Pinning-bump tracking (v2).
- ❌ Status-dashboard active-migration scraping (v2).
- ❌ Auto-`/schedule`d audit (v2).

---

## References

- **`CLAUDE.md` § Conda-Forge Ecosystem Reference** — authoritative map
  of repos, docs, CFEPs, tooling, and community personas the tracker
  surfaces in templates.
- **`local-recipes/.claude/skills/conda-forge-expert/SKILL.md`** —
  source of `update_recipe`, `update_recipe_from_github`,
  `check_github_version`, `scan_for_vulnerabilities`, and
  `analyze_build_failure`. Bridged via `_cf_tools.py`.
- **`docs/enterprise-deployment.md`** — air-gapped/Artifactory pattern;
  informs the offline-friendly design.
- **`docs/specs/copilot-bridge-vscode-extension.md`** — sibling BMAD
  spec; format reference.
- **`regro/cf-graph-countyfair`** — discovery data source.
  <https://github.com/regro/cf-graph-countyfair>
- **`prefix-dev/parselmouth`** — "package on conda-forge?" check.
  <https://conda-mapping.prefix.dev/pypi-to-conda-v1/conda-forge/>
- **conda-forge admin-requests** — `mark-broken-yank` channel target.
  <https://github.com/conda-forge/admin-requests>
- **conda-forge webservices** — `feedstock-comment` channel target.
  <https://github.com/conda-forge/webservices>
- **BMAD Method docs** — `.claude/docs/bmad-method-llms-full.txt`
  (offline) / <https://docs.bmad-method.org/llms-full.txt> (live).

---

## Suggested BMAD Invocation

This spec is structured for `bmad-quick-dev`. Either:

```
# Single shot — let bmad-quick-dev plan + implement story-by-story:
run quick-dev — implement docs/specs/conda-forge-tracker.md
```

or, if full BMAD Method discipline is preferred (PRD → Architecture
→ Stories → Implementation):

```
# Phase 2 (Planning) — feed this spec as the brief input:
bmad-create-prd --brief docs/specs/conda-forge-tracker.md

# Phase 3 (Solutioning):
bmad-create-architecture
bmad-create-epics-and-stories

# Phase 4 (Implementation):
bmad-sprint-planning
bmad-dev-story        # repeat per story
```

Quick Flow is recommended for this scope (13 stories, single Python
package directory, well-bounded surface). The full Method path is
overkill but documented for completeness.
