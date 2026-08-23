# pyforge-testing-kit

Shared test-support kit for PyForge stations (FR-130 / Story 19.2). Four
mock families, seeded from Marshal's already-real mocks rather than rewritten:

| Family | Module | Seed |
|--------|--------|------|
| CLI-runner | `pyforge.testing_kit.cli_runner` | `mock_runner.py` |
| page-object | `pyforge.testing_kit.page_object` | `mock_worktree.py` |
| DB-factory | `pyforge.testing_kit.db_factory` | `mock_supervisor.py` + conftest store factories |
| auth/HTTP/time | `pyforge.testing_kit.auth_http_time` | `mock_github_api.py` + supervisor timing |

**Q-26 decision:** own leaf package (not `pyforge.core.testing`) — keeps
test-only fixtures out of every station's runtime `pyforge-core` install.

## Develop

Run from the repository root:

```bash
pixi run -e pyforge-testing-kit pyforge-testing-kit-test
```
