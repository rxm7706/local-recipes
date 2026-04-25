# Conda-Forge Bot Commands

Commands for interacting with the conda-forge bot in GitHub pull requests and issues.

## @conda-forge-admin Commands

Use these commands by commenting on a PR or issue in a conda-forge feedstock or staged-recipes.

### CI Management

```
@conda-forge-admin, please rerender
```
Regenerates the CI configuration files (`.azure-pipelines/`, `.github/workflows/`, etc.) using conda-smithy. Use after changing `conda-forge.yml` or to pick up infrastructure updates.

```
@conda-forge-admin, please restart ci
```
Restarts all CI jobs. Useful when a transient failure occurs (network issues, timeouts, etc.).

```
@conda-forge-admin, please lint
```
Runs the recipe linter on the PR.

### Recipe Modifications

```
@conda-forge-admin, please add noarch: python
```
Adds `noarch: python` to the recipe.

```
@conda-forge-admin, please update version
```
Triggers an automatic version update check.

### Team Management

```
@conda-forge-admin, please add user @username
```
Adds a user as a maintainer to the feedstock.

```
@conda-forge-admin, please remove user @username
```
Removes a user from the feedstock maintainers.

```
@conda-forge-admin, please update team
```
Syncs the team membership based on the recipe's `extra.recipe-maintainers` list.

### Automerge

```
@conda-forge-admin, please add bot automerge
```
Enables automatic merging of bot-created PRs (version updates, migrations).

```
@conda-forge-admin, please remove bot automerge
```
Disables automatic merging.

### Archive/Transfer

```
@conda-forge-admin, please archive
```
Archives the feedstock repository.

```
@conda-forge-admin, please regenerate github actions yaml
```
Regenerates only the GitHub Actions workflow files.

## Review Team Mentions

Request review from specialized teams:

```
@conda-forge/help-python ready for review
```

```
@conda-forge/help-python-c ready for review
```

```
@conda-forge/help-c-cpp ready for review
```

```
@conda-forge/help-rust ready for review
```

```
@conda-forge/help-r ready for review
```

```
@conda-forge/help-nodejs ready for review
```

```
@conda-forge/staged-recipes ready for review
```

```
@conda-forge/core
```
Mentions the core team (use sparingly, for important issues).

## Bot Configuration in conda-forge.yml

Configure bot behavior in `conda-forge.yml`:

```yaml
bot:
  # Enable automerge for bot PRs
  automerge: true

  # Inspection level for version updates
  inspection: hint-all      # hint-all, update-grayskull, update-all

  # Check if package is solvable
  check_solvable: true

  # Extract run dependencies from wheel metadata
  run_deps_from_wheel: true
```

### Inspection Levels

| Level | Description |
|-------|-------------|
| `hint-all` | Provides hints about updates (default) |
| `update-grayskull` | Uses grayskull to update recipe |
| `update-all` | Attempts comprehensive updates |

### Selecting a CI Provider per Platform (conda-smithy 3.57.1+, Mar 2026)

```yaml
# conda-forge.yml
provider:
  linux_64: github_actions    # opt into GitHub Actions for native Linux builds
  # linux_aarch64: cirun       # native ARM via Cirun on supported feedstocks
  # osx_64: azure              # default; explicit for clarity
  # win_64: azure              # default
```

Rerender after editing (`conda-smithy rerender` or `@conda-forge-admin, please rerender`) so the generated CI files match.

### Excluding Erroneous Upstream Versions

```yaml
# conda-forge.yml — keep the bot from picking up bad upstream tags
bot:
  version_updates:
    exclude:
      - "1.0.0rc1"
      - "1.0.0+post"
```

## Useful PR Checklist Comments

When submitting to staged-recipes, include this checklist:

```markdown
Checklist:
- [x] Title is meaningful (e.g., "Adding my-package")
- [x] License file is packaged
- [x] Source is from official source
- [x] Package does not vendor other packages
- [x] Build number is 0
- [x] Using tarball (url) not git repository
- [x] Maintainers have confirmed participation
```

## Common Bot Issues

### "Rerender failed"

The bot couldn't regenerate CI files. Try:
1. Run `conda-smithy rerender` locally
2. Push the changes
3. Comment `@conda-forge-admin, please rerender` again

### "CI timed out"

```
@conda-forge-admin, please restart ci
```

### "Missing review"

```
@conda-forge/staged-recipes ready for review
```

### "Merge conflict with migrations"

```
@conda-forge-admin, please rerender
```

## Autotick Bot

The autotick bot automatically creates PRs for:
- Version updates
- Dependency migrations
- Infrastructure updates

### Closing Bot PRs

If a bot PR is incorrect:
```
@conda-forge-admin, please close
```

### Regenerating Bot PRs

If the bot PR needs updating:
```
@conda-forge-admin, please rerun bot
```
