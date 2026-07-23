# CLAUDE.md Templates Guide

This collection provides starter CLAUDE.md templates for different types of Python projects. Choose the template that best matches your project type.

## What is CLAUDE.md?

CLAUDE.md is a configuration file that Claude Code automatically reads when working in your project directory. It provides:
- Project context and structure
- Development commands
- Code style conventions
- Workflow guidelines

**Key Point**: Claude Code treats CLAUDE.md instructions as authoritative system rules with higher priority than user prompts.

## Available Templates

### 1. **python-minimal-CLAUDE.md** 
**Best for**: Small scripts, quick projects, learning
- Minimal configuration
- Essential commands only
- Quick reference format
- Perfect for simple Python scripts

### 2. **python-basic-CLAUDE.md**
**Best for**: General Python projects, CLI tools, libraries
- Comprehensive Python project setup
- uv package management
- Testing and linting setup
- Git workflow guidelines
- File organization tips

### 3. **python-fastapi-CLAUDE.md**
**Best for**: Web APIs, microservices, REST APIs
- FastAPI-specific conventions
- Database integration (SQLAlchemy)
- API endpoint design patterns
- Authentication and security
- Testing async code
- Production-ready configurations

### 4. **python-datascience-CLAUDE.md**
**Best for**: Data analysis, machine learning, research
- Data pipeline workflows
- Jupyter notebook guidelines
- Feature engineering patterns
- Model training best practices
- Experiment tracking
- Reproducibility guidelines

### 5. **python-mcp-server-CLAUDE.md**
**Best for**: Building MCP (Model Context Protocol) servers
- MCP server setup with FastMCP
- Tool, resource, and prompt patterns
- Claude Desktop integration
- Logging best practices for STDIO servers
- Debugging and troubleshooting

## How to Use These Templates

### Step 1: Choose Your Template
Pick the template that matches your project type.

### Step 2: Copy to Your Project
```bash
# Copy the template to your project root
cp python-basic-CLAUDE.md /path/to/your/project/CLAUDE.md
```

### Step 3: Customize
Edit the CLAUDE.md file to match your specific project:
- Update tech stack versions
- Add project-specific commands
- Include custom conventions
- Add team-specific guidelines

### Step 4: Use with Claude Code
Claude Code automatically reads CLAUDE.md when you start working in your project directory.

## Common Sections Explained

### Project Overview
Brief description of what your project does and its primary purpose.

### Tech Stack
List of technologies, frameworks, and their versions. Keep this updated!

### Package Management
Commands for installing, updating, and managing dependencies. All templates use `uv` by default.

### Project Structure
Directory layout and what each folder contains. Helps Claude understand your organization.

### Development Commands
Common commands you run during development (testing, linting, running servers, etc.).

### Code Style & Conventions
Your project's specific style rules, naming conventions, and patterns.

### Git Workflow
Branch naming, commit message format, and what to commit or ignore.

## Key Best Practices

### 1. Keep It Updated
Update CLAUDE.md when you:
- Change dependencies
- Add new tools or commands
- Modify project structure
- Update conventions

### 2. Be Specific
- Include exact commands with flags
- Specify file paths
- Document expected behavior
- Provide examples

### 3. Document Edge Cases
- Special setup requirements
- Platform-specific commands
- Common gotchas
- Troubleshooting tips

### 4. Team Consistency
- Commit CLAUDE.md to Git
- Review changes in pull requests
- Keep it as single source of truth
- Use CLAUDE.local.md for personal preferences

## Combining with Other Files

### CLAUDE.local.md (Personal)
Personal preferences that shouldn't be shared:
```markdown
# CLAUDE.local.md (add to .gitignore)
## My Personal Preferences
- Use vim keybindings
- Skip certain linting rules
```

### Custom Commands
Create custom slash commands in `.claude/commands/`:
```markdown
# .claude/commands/deploy.md
Deploy the application:
1. Run tests
2. Build Docker image
3. Push to registry
4. Update Kubernetes deployment
```

## Tips for Maximum Effectiveness

### Start Simple
Begin with a minimal template and add details as you discover what Claude needs to know.

### Use Clear Sections
Break information into logical markdown sections to prevent "instruction bleeding."

### Avoid Overloading
Only include information relevant to current work. Too much context can reduce predictability.

### Test and Iterate
- Test how Claude responds to your CLAUDE.md
- Refine based on what works
- Remove unnecessary details

### Document the "Why"
Explain not just what to do, but why certain patterns are used.

## Common Pitfalls to Avoid

❌ **Don't**: Include secrets or API keys
✅ **Do**: Use environment variables

❌ **Don't**: Make it too long and unfocused
✅ **Do**: Keep it concise and relevant

❌ **Don't**: Forget to update when project changes
✅ **Do**: Treat it as living documentation

❌ **Don't**: Copy without customizing
✅ **Do**: Adapt to your specific needs

## Example Customization

### Before (Generic)
```markdown
## Tech Stack
- Python 3.11+
- FastAPI
```

### After (Specific)
```markdown
## Tech Stack
- Python 3.11.5 (managed with pyenv)
- FastAPI 0.104.1
- PostgreSQL 15.3
- Redis 7.0 (for caching)
- Celery 5.3 (for background tasks)
```

## Integration with Development Tools

### Pre-commit Hooks
Reference your CLAUDE.md standards in `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: ruff-format
        entry: uv run ruff format
        language: system
```

### VS Code Settings
Align your `.vscode/settings.json` with CLAUDE.md conventions:
```json
{
  "python.formatting.provider": "none",
  "python.linting.enabled": false,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  }
}
```

## Additional Resources

- **Official Claude Code Docs**: https://www.anthropic.com/engineering/claude-code-best-practices
- **Awesome Claude Code**: https://github.com/hesreallyhim/awesome-claude-code
- **MCP Documentation**: https://modelcontextprotocol.io/
- **uv Documentation**: https://docs.astral.sh/uv/

## Getting Help

If Claude isn't following your CLAUDE.md:
1. Check for syntax errors in your markdown
2. Ensure instructions are clear and specific
3. Try breaking complex rules into smaller sections
4. Test with simpler instructions first
5. Remember: CLAUDE.md has higher priority than prompts

## Quick Reference

| Template | Use Case | Key Features |
|----------|----------|--------------|
| Minimal | Scripts, small projects | Essential commands only |
| Basic | General Python | Full project structure |
| FastAPI | Web APIs | Async, database, security |
| Data Science | ML, analysis | Notebooks, experiments |
| MCP Server | MCP servers | Tools, resources, prompts |

## Next Steps

1. Choose your template
2. Copy to your project as `CLAUDE.md`
3. Customize for your needs
4. Start using Claude Code
5. Iterate based on experience

Happy coding with Claude! 🚀