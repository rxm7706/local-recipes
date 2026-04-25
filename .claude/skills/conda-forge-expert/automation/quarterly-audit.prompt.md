---
purpose: Quarterly live-doc audit of the conda-forge-expert skill
runs-on: Both the remote routine (cloud sandbox) and run-audit-local.sh (local CLI)
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch]
---

You are running a quarterly live-documentation audit of the `conda-forge-expert` skill in this repo. Goal: detect changes upstream in the conda-forge ecosystem since the previous audit and incrementally upgrade the skill (refs, templates, guides, quickref, SKILL.md), then open a PR.

## Context

The skill lives at `.claude/skills/conda-forge-expert/`. Read these first to anchor the current state:

- `.claude/skills/conda-forge-expert/SKILL.md` — note the version field in frontmatter and the latest entry under `## Version History` at the bottom. That entry summarizes what the previous audit changed; treat it as the baseline.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — top entry mirrors the SKILL.md version-history entry.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — `skill.version` field.
- `CLAUDE.md` (repo root) — project conventions and Karpathy-style behavioral guidelines. Apply them: surgical changes, simplicity first, no speculative edits.

## Sources to fetch (use WebFetch)

Compare each of these against what the skill currently encodes. Focus on entries dated **after** the previous audit's date (in the latest CHANGELOG entry).

1. https://conda-forge.org/news/ — news items; flag anything affecting recipe authoring, CI, compilers, Python/NumPy matrix, OS versions, build tooling, MPI/CUDA/macOS, governance/policy/CFEPs.
2. https://conda-forge.org/docs/maintainer/adding_pkgs/ — new-recipe requirements; check for changes to license rules, test rules, format guidance.
3. https://conda-forge.org/docs/maintainer/knowledge_base/ — knowledge-base entries; check for new platform-specific guidance.
4. https://conda-forge.org/docs/maintainer/infrastructure/ — CI providers per platform, OS versions, build limits.
5. https://raw.githubusercontent.com/conda-forge/conda-forge-pinning-feedstock/main/recipe/conda_build_config.yaml — current global pins (python, python_min, numpy, c/cxx/fortran compilers per platform, cuda, openssl, boost, hdf5, arrow, pytorch, qt/qt6).
6. https://github.com/prefix-dev/rattler-build/releases — list releases since the version cited in the latest skill changelog entry; capture every breaking change, new flag, schema change, and removed CLI option.
7. https://conda-forge.org/status/ — currently active migrations; record any that affect ABI pins or compiler upgrades.
8. https://github.com/conda-forge/cfep — list CFEPs and identify any newly accepted since the previous audit.

## Files to update (only when upstream actually changed)

Apply surgical edits — do not refactor adjacent content, do not invent improvements, do not touch files where nothing material has changed upstream.

- `.claude/skills/conda-forge-expert/SKILL.md`:
  - `## CI Infrastructure Reference` — provider table, build-time limits, OS versions, compiler pins.
  - `## Ecosystem Updates (Apr 2026)` section — replace the date in the heading with the new audit's month/year and refresh entries; carry forward only entries that are still relevant (drop ones older than ~12 months unless still load-bearing).
  - Community Channels table — sync if Zulip/Discourse/Gitter status changes.
  - Frontmatter `version:` — bump patch (e.g. 5.9.0 → 5.10.0).
  - Add a new entry to `## Version History` describing the audit.
- `.claude/skills/conda-forge-expert/reference/pinning-reference.md` — global-pins table, MPI/CUDA platform-specific sections.
- `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md` — rattler-build version-specific subsections (env-isolation, debug subcommand, multi-output script discovery, anything new). Update `## 2025–2026 Platform Updates` and the macOS SDK directory if upstream changes it.
- `.claude/skills/conda-forge-expert/reference/selectors-reference.md` — Python skip examples if the build matrix floor moves.
- `.claude/skills/conda-forge-expert/templates/` — sweep for obsolete `py < N` skips when the floor advances; remove or rewrite stale comments. Update multi-output templates if rattler-build changes script discovery.
- `.claude/skills/conda-forge-expert/guides/ci-troubleshooting.md` — CI Platform Assignment table, community channels (Resources section).
- `.claude/skills/conda-forge-expert/guides/feedstock-maintenance.md` — Build/Test/Automerge stage table, Resources section.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — rattler-build flags, env-isolation modes, debug subcommand.
- `.claude/skills/conda-forge-expert/quickref/bot-commands.md` — `provider:` config, `bot.version_updates.exclude`, any new `@conda-forge-admin` commands.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — add a new entry at the top describing every change.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — bump `skill.version` to match SKILL.md.

## Workflow

1. Read the existing skill files listed under Context above. Note the current version, the date of the last audit, and the known state of upstream (CI providers, compiler pins, rattler-build version, Python matrix, etc.).
2. WebFetch each source. For each, write a one-line delta vs. what the skill currently encodes — no delta = no edit.
3. Apply minimal edits. Use the `Edit` tool with exact-string matches; do not rewrite whole files when a few lines change.
4. Bump the patch version everywhere it appears: SKILL.md frontmatter, SKILL.md version history, CHANGELOG.md, config/skill-config.yaml.
5. If `npm`/`pixi`/build tooling exists for the skill, do **not** run it — just edit text.
6. Commit on a new branch named `chore/conda-forge-expert-audit-YYYY-MM` (replace with the current YYYY-MM). Commit message: `chore(conda-forge-expert): quarterly live-doc audit YYYY-MM` followed by a short bullet list of source-grouped changes. Co-author: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
7. Push the branch and open a PR via `gh pr create` against `main`. PR title: `chore(conda-forge-expert): quarterly live-doc audit YYYY-MM`. PR body: Summary section with one bullet per source that produced changes, then a Test Plan checklist (`Validate skill loads`, `Spot-check version bumps in SKILL.md/CHANGELOG.md/skill-config.yaml`, `Skim updated tables for accuracy`).
8. If **no** upstream sources show material changes, do nothing — do not bump the version, do not open a noise-only PR. Instead, append a one-line entry to a file `.claude/skills/conda-forge-expert/automation/AUDITS.log` (create it if missing) recording `YYYY-MM-DD: no changes`, commit on `main`, and push directly. (If push to main is rejected, open a PR titled `chore(conda-forge-expert): no-op quarterly audit YYYY-MM` instead.)

## Guardrails

- Do not edit `.claude/tools/conda_forge_server.py` or any Python script under `.claude/skills/conda-forge-expert/scripts/` — those are out of scope for a doc audit.
- Do not migrate any actual recipe in `recipes/`. This audit only edits the skill itself.
- Do not delete pre-existing version history entries in SKILL.md or CHANGELOG.md.
- Do not touch unrelated repo files (recipes, .pixi, .idea, etc.).
- If a source URL fails (404, redirect), record it in the PR body but continue with the others. Do not block the audit on one source.
- If the GitHub remote is misconfigured or `gh auth` fails, stop and write findings to `/tmp/audit-YYYY-MM.md` rather than partially committing.

Report at the end: branch name, PR URL (or 'no-op' if no changes), and a one-paragraph summary of what changed.
