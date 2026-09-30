# pyforge-testing-kit

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Shared test-support kit for PyForge stations (FR-130 / Story 19.2). Four
mock families, seeded from Marshal's already-real mocks rather than rewritten,
and a fifth, the feature-flag family (`spec-feature-flag-governance` CAP-4):

| Family | Module | Seed |
|--------|--------|------|
| CLI-runner (`MockRunner`; `invoke_cli` / `CliResult`, which run a station's `main(argv)` in-process and return its exit code and output) | `pyforge.testing_kit.cli_runner` | `mock_runner.py` |
| page-object | `pyforge.testing_kit.page_object` | `mock_worktree.py` |
| DB-factory | `pyforge.testing_kit.db_factory` | `mock_supervisor.py` + conftest store factories |
| auth/HTTP/time | `pyforge.testing_kit.auth_http_time` | `mock_github_api.py` + supervisor timing |
| feature-flag | `pyforge.testing_kit.flags` | `src/platform/tests/test_openfeature_file_flags.py`'s hand-written flagd tree |

**Q-26 decision:** own package (not `pyforge.core.testing`) — keeps
test-only fixtures out of every station's runtime `pyforge-core` install. The
kit itself depends on `pyforge-core` (its git calls run through
`pyforge.core.process`) and on `openfeature-sdk` (the flag family); `pyforge-core`
does not depend on the kit.

## Feature-flag family

Run a flagged story in both flag states through OpenFeature's `InMemoryProvider`
(`spec-feature-flag-governance` CAP-4). Bind the fixture once in the station's
`conftest.py`, or a test using it fails with `fixture 'flag_provider' not found`:

```python
# conftest.py
from pyforge.testing_kit import make_flag_provider_fixture

flag_provider = make_flag_provider_fixture()

# a test module
from pyforge.testing_kit import assert_flag_off_verb, flag_states


@flag_states("pyforge.example.thing")  # runs twice: ids `on` and `off`
def test_the_capability(): ...


def test_the_verb_when_its_flag_is_off():
    assert_flag_off_verb(main, "thing", usage_code)  # listed in --help as disabled; exits with usage_code
```

For integration tests, and for Playwright against a server started on it,
`flagd_tree(tmp_path, {"pyforge.example.thing": "off"})` writes a temporary flagd
FILE tree in the shape of `src/platform/config/flags.json` and returns its path.

## Develop

Run from the repository root:

```bash
pixi run -e pyforge-testing-kit pyforge-testing-kit-test
```
