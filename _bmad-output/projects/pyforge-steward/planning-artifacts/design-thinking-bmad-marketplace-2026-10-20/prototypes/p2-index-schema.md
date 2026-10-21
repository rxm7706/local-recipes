# P2 — Index entry format: notes (paper prototype)

**One file per listing (`listing.yaml` next to the SKILL.md) → CI builds one `index.yaml`/`index.json`.**
Pages, `bmp search`, and every per-tool manifest are generated from that index. Nobody hand-edits a tool manifest.

**Compatibility with v1.** v1's `registry/estate.yaml` uses the upstream bmad-plugins-marketplace registry schema
(`registry/registry-schema.yaml`: name, display_name, code, description, repository, author, license, type,
category, subcategory, keywords, version, trust_tier). The prototype keeps those keys unchanged and adds new ones
(scope, kind, summary, tasks, owners, tier, requires, install, adapters, sources, checksums, verified_at, ci, docs,
lane, bundles). An entry stays a valid upstream row once you strip the new keys. `catalog.py`'s
`EstateListingsSource` already reads name/description/repository/version/trust_tier.

**Trust tiers.** You named three tiers; each maps onto the upstream `trust_tier` enum:

| bmp `tier` | upstream `trust_tier` | Meaning |
|---|---|---|
| bmad-certified | bmad-certified | Upstream official module already in the wielded suite |
| estate-reviewed | community-reviewed | A CODEOWNER approved it; review record in `reviews/` |
| community | unverified | Passed lint + CI only |

**Names.** `@scope/slug`. Scope is a station (`mason`, `scribe`, …), `bmad` for upstream, or a teammate handle.
Install folder = `<scope>-<slug>` (`mason-environment`) so it fits each tool's lowercase-hyphen skill-name rule.
*Open: the station persona agents are already named `bmad-agent-<station>`. Keep those names or rename them to `@station/agent`?*

**Agents.** The portable core is always the persona skill. `adapters` are generated at install time, and only into
formats confirmed in `tool-support-matrix.md`. Unconfirmed formats carry `confirmed: false`, and `bmp` skips them
unless `--experimental-adapters` is set. `requires` entries of kind `service`/`bmad-project` can be `optional` with
a `degraded_mode`. That is how a station-server agent installs on a machine with no server.

**Sources.** The same tagged build produces a GitHub release zip and Artifactory conda/pip packages. `checksums`
must match across sources, and `bmp` verifies before writing files. Upstream modules keep their upstream tarball plus
the conda package already in `recipes/bmad-*`.

**Generating per-tool manifests from the index** (optional outputs, not the backbone):

| Output | Built from | Notes |
|---|---|---|
| Claude Code `.claude-plugin/marketplace.json` | each listing → one plugin entry; `source` = `git-subdir` (internal repo + folder) or `url` | v1's renderer in `catalog.py` already writes this file; switch from `github` pointers to `git-subdir`/`url` so internal hosts work |
| Codex `.agents/plugins/marketplace.json` | same entries, `source.path` relative to the marketplace root | v1 already renders an (empty) file |
| VS Code agent plugins `marketplace.json` | same, for `chat.plugins.marketplaces` | format details unconfirmed for GHE/GitLab |
| Devin `.devin-plugin/plugin.json` (meta-plugin) | `optionalPlugins` = listings | mirrors Cognition's team-marketplace template |
| Gemini CLI extension | a bundle → `gemini-extension.json` + `skills/` | per bundle, not per skill |
| Cursor | none generated: Cursor reads `.agents/skills` and `.claude/skills` directly | Cursor Marketplace private hosting unconfirmed |
| Pages | every listing → a card (P3) + `index.json` | the browse surface for every teammate |

**Fields left out on purpose:** download counts and usage telemetry (pull them from Artifactory/GitHub stats),
billing, and Frames.
