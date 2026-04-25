# Feedstock Maintenance Guide

Complete guide for maintaining conda-forge feedstocks after initial package submission.

## Maintenance Git Workflow

*From `git-workflow-and-versioning` + `ci-cd-and-automation`. Apply these disciplines to all maintenance PRs.*

### Branch Discipline

Every maintenance change gets its own branch — never commit directly to `main`:

| Change Type | Branch Name Pattern | PR Size Rule |
|-------------|-------------------|--------------|
| Version bump | `update-v1.2.3` | One package per PR |
| Dependency pin | `pin-numpy-2.0` | One dependency group per PR |
| Recipe migration | `migrate-to-v1` | One feedstock per PR — never bundle |
| Bug fix | `fix-build-linux` | Smallest possible change |
| Rerender | `rerender-ci-update` | CI files only — no recipe changes |

### Commit Message Convention

```
<type>: <one-line summary>

# Types:
# update  — new upstream version
# fix     — build/test fix
# pin     — dependency version change
# maint   — infrastructure / rerender
# migrate — format migration (meta.yaml → recipe.yaml)
```

Example: `update: bump numpy to 2.1.0, reset build number`

### Understanding the conda-forge CI/CD System

The bot and CI form an automated pipeline. Understand what each component checks:

| Stage | Tool | Triggers | What it checks |
|-------|------|---------|----------------|
| Lint | conda-smithy | PR open/push | Recipe policy, required fields |
| Solve | conda-build/rattler | Every build | Dependency availability across platforms |
| Build | Azure/GitHub Actions | Every push | Compilation, packaging |
| Test | conda test | Post-build | Import, CLI, file presence |
| Automerge | cf-autotick-bot | After CI green | Version updates only |

**Shift-left principle**: run `pixi run lint` and `python build-locally.py` before pushing — catching failures locally is faster than waiting for CI.

### When to Rerender vs. Edit

- **Rerender** (`conda-smithy rerender`): when CI YAML files are out of date, after adding a new platform, or when the bot requests it. Never edit `.azure-pipelines/` or `.github/workflows/` by hand.
- **Edit recipe**: when changing package content, version, or requirements.
- **Never mix**: a rerender PR and a recipe change PR should be separate.

---

## Maintainer Responsibilities

As a feedstock maintainer, you are responsible for:

1. **Version Updates** - Keep package current
2. **Bug Fixes** - Address build/test issues
3. **Dependency Updates** - Handle migrations
4. **User Support** - Respond to issues
5. **Security** - Address vulnerabilities promptly

## Version Updates

### Automatic Updates (Recommended)

The conda-forge bot automatically creates PRs for new versions.

**Enable automerge:**
```yaml
# conda-forge.yml
bot:
  automerge: true
  inspection: hint-all
  run_deps_from_wheel: true
```

**Inspection levels:**
| Level | Description |
|-------|-------------|
| `hint-all` | Shows hints, manual merge |
| `update-grayskull` | Auto-updates using grayskull |
| `update-all` | Comprehensive auto-updates |

### Manual Version Updates

```bash
# 1. Clone feedstock
git clone https://github.com/conda-forge/my-package-feedstock
cd my-package-feedstock

# 2. Create branch
git checkout -b update-version

# 3. Update recipe
# Edit recipe/recipe.yaml or recipe/meta.yaml:
# - Update version
# - Update sha256
# - Reset build number to 0

# 4. Get new hash
curl -sL "https://pypi.org/packages/source/m/my-package/my-package-NEW_VERSION.tar.gz" | sha256sum

# 5. Commit and push
git add recipe/
git commit -m "Update to version X.Y.Z"
git push origin update-version

# 6. Create PR
gh pr create --title "Update to X.Y.Z"
```

### Version Update Checklist

- [ ] Update version number
- [ ] Update source hash
- [ ] Reset build number to 0
- [ ] Check if dependencies changed
- [ ] Check if build process changed
- [ ] Update patches if needed

## Build Number Management

### When to Increment

Increment build number (don't reset to 0) when:
- Fixing recipe without version change
- Adding/removing dependencies
- Changing build configuration
- Applying patches

```yaml
build:
  number: 1  # Was 0, incremented for fix
```

### When to Reset

Reset to 0 when:
- Updating package version
- After major migrations

## Handling Migrations

### What are Migrations?

Migrations update packages for:
- Compiler updates (GCC 12 → 13)
- Python version additions (3.12 support)
- Dependency ABI changes (OpenSSL 3.0)
- Infrastructure changes

### Responding to Migration PRs

1. **Review the PR** - Check changes make sense
2. **Test locally** if unsure
3. **Merge** if CI passes
4. **Request help** if issues

```bash
# Comment to re-run bot
@conda-forge-admin, please rerun bot

# Request rerender
@conda-forge-admin, please rerender
```

### Common Migrations

| Migration | Impact | Action |
|-----------|--------|--------|
| Python version | New Python variant | Usually automatic |
| NumPy 2.0 | ABI change | May need code fixes |
| OpenSSL 3.0 | API changes | Review build |
| GCC update | Compiler change | Usually automatic |

## Patching Upstream

### Creating Patches

```bash
# 1. Clone upstream
git clone https://github.com/upstream/project
cd project
git checkout v1.2.3

# 2. Make changes
# Edit files to fix issue

# 3. Create patch
git diff > fix-issue.patch

# 4. Add to recipe
mv fix-issue.patch /path/to/feedstock/recipe/
```

### Using Patches

```yaml
# recipe.yaml
source:
  url: https://...
  sha256: ...
  patches:
    - fix-issue.patch
    - 0001-another-fix.patch

# meta.yaml
source:
  url: https://...
  sha256: ...
  patches:
    - fix-issue.patch
```

### Patch Best Practices

1. **Minimal changes** - Only fix the issue
2. **Document** - Add comment explaining why
3. **Upstream first** - Submit fix upstream
4. **Remove when fixed** - Delete patch after upstream release

## Adding/Removing Maintainers

### Add Maintainer

```bash
# Via PR - edit recipe
extra:
  recipe-maintainers:
    - existing-maintainer
    - new-maintainer      # Add here

# Via bot command
@conda-forge-admin, please add user @username
```

### Remove Maintainer

```bash
# Via bot command
@conda-forge-admin, please remove user @username

# Or edit recipe and create PR
```

### Sync Team

```bash
@conda-forge-admin, please update team
```

## Handling Issues

### Common Issue Types

| Issue Type | Response |
|------------|----------|
| Build failure | Check CI logs, fix recipe |
| Missing dependency | Add to requirements |
| Version request | Create update PR or wait for bot |
| Bug in package | Direct to upstream |
| Feature request | Direct to upstream |

### Issue Templates

**Build failure response:**
```markdown
Thanks for reporting! I see the build is failing because [reason].

I've created a fix in PR #XX. This should be resolved once merged.
```

**Upstream issue:**
```markdown
This looks like an issue in the upstream package, not the conda-forge recipe.

Please report this at: [upstream issue tracker URL]

Once fixed upstream and released, we'll get the update automatically.
```

## Deprecating Packages

### When to Deprecate

- Package abandoned upstream
- Replaced by another package
- Security issues unaddressed

### How to Deprecate

```yaml
# Add deprecation notice
about:
  summary: "[DEPRECATED] Use new-package instead. Original description..."

# Add run_constrained for replacement
requirements:
  run_constrained:
    - new-package >=1.0  # Suggest replacement
```

### Archive Feedstock

```bash
@conda-forge-admin, please archive
```

## Multi-Output Maintenance

### Coordinating Outputs

All outputs share the same:
- Build number
- Source
- CI infrastructure

Update all outputs together:

```yaml
# Update version in context
context:
  version: "2.0.0"  # All outputs use this

# Each output automatically updated
outputs:
  - package:
      name: libfoo
      version: ${{ version }}
  - package:
      name: foo
      version: ${{ version }}
```

## CI Configuration

### conda-forge.yml Options

```yaml
# Build configuration
build:
  error_overlinking: true
  error_overdepending: true

# Bot settings
bot:
  automerge: true
  inspection: hint-all
  check_solvable: true
  run_deps_from_wheel: true

# Platform skipping
skip_render:
  - win

# Extra channels
channels:
  targets:
    - [main, conda-forge]

# CI provider settings
azure:
  store_build_artifacts: true

github_actions:
  triggers:
    push:
      branches:
        - main
```

### Rerendering

After changing conda-forge.yml:

```bash
# Local
conda-smithy rerender

# Via bot
@conda-forge-admin, please rerender
```

## Security

### Handling Vulnerabilities

1. **Check if affected** - Review CVE details
2. **Update immediately** - If fix available upstream
3. **Patch if needed** - If no upstream fix yet
4. **Notify users** - For critical issues

### Security Best Practices

```yaml
# Pin to secure versions
requirements:
  run:
    - openssl >=3.0.7  # Security fix

# Use run_constrained for conflicts
requirements:
  run_constrained:
    - vulnerable-package <1.0  # Block vulnerable versions
```

## Monitoring

### Watch for Updates

```bash
# Watch feedstock
gh repo subscribe conda-forge/my-package-feedstock

# Check package status
mamba search -c conda-forge my-package
```

### Track Dependencies

```bash
# What depends on my package?
mamba repoquery whoneeds my-package -c conda-forge

# What does my package need?
mamba repoquery depends my-package -c conda-forge
```

## Best Practices Summary

1. **Respond promptly** - Check feedstock weekly
2. **Enable automerge** - For routine updates
3. **Test locally** - Before merging complex changes
4. **Document changes** - Clear commit messages
5. **Coordinate** - With co-maintainers on big changes
6. **Stay current** - Follow conda-forge announcements
7. **Ask for help** - When unsure

## Resources

- [Maintainer Documentation](https://conda-forge.org/docs/maintainer/)
- [Status Dashboard](https://conda-forge.org/status/)
- [conda-forge Blog](https://conda-forge.org/blog/)
- [Gitter Chat](https://gitter.im/conda-forge/conda-forge.github.io)
