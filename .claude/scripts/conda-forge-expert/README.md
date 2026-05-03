# .claude/scripts/conda-forge-expert/

**Stable public entrypoint layer** for conda-forge-expert tooling.

These files are the surface you call from `pixi run ...`, CI, or directly from the
shell. They are thin subprocess wrappers — no logic lives here.

## Architecture

```
.claude/
├── scripts/
│   └── conda-forge-expert/   ← YOU ARE HERE (stable public CLI entrypoints)
│       ├── *.py              ← wrapper per script
│       └── README.md
├── skills/
│   └── conda-forge-expert/
│       ├── scripts/          ← canonical implementation (source of truth)
│       ├── templates/
│       ├── reference/
│       ├── guides/
│       └── tests/
└── data/
    └── conda-forge-expert/   ← all mutable runtime state (not in git)
        ├── cf_atlas.db
        ├── vdb/
        ├── cve/
        └── ...
```

## Rules

- **Add new scripts here** when adding a new pixi task or public CLI.
- **Put all logic in** `.claude/skills/conda-forge-expert/scripts/<name>.py`.
- **Wrappers must stay thin** — one `subprocess.run` call, no logic.
- **Internal/private scripts** (`_sbom.py`, `test-skill.py`, `recipe_editor.py`) do NOT get wrappers.

## Wrapper pattern

```python
#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path
_SKILL_SCRIPT = Path(__file__).parent.parent.parent / "skills" / "conda-forge-expert" / "scripts" / "my_script.py"
if __name__ == "__main__":
    sys.exit(subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:]).returncode)
```

## Adding a new script

1. Write the implementation in `.claude/skills/conda-forge-expert/scripts/my_script.py`
2. Create a wrapper here using the pattern above
3. Add a pixi task in `pixi.toml` pointing to this wrapper path:
   ```toml
   [feature.local-recipes.tasks.my-task]
   cmd = "python .claude/scripts/conda-forge-expert/my_script.py"
   ```

