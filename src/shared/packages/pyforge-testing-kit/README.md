# pyforge-testing-kit

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Shared test-support kit for PyForge stations (FR-130 / Story 19.2). Four
mock families, seeded from Marshal's already-real mocks rather than rewritten,
a fifth, the feature-flag family (`spec-feature-flag-governance` CAP-4), and two
shared guard helpers:

| Family | Module | Seed |
|--------|--------|------|
| CLI-runner (`MockRunner`; `invoke_cli` / `CliResult`, which run a station's `main(argv)` in-process and return its exit code and output) | `pyforge.testing_kit.cli_runner` | `mock_runner.py` |
| page-object | `pyforge.testing_kit.page_object` | `mock_worktree.py` |
| DB-factory | `pyforge.testing_kit.db_factory` | `mock_supervisor.py` + conftest store factories |
| auth/HTTP/time | `pyforge.testing_kit.auth_http_time` | `mock_github_api.py` + supervisor timing |
| feature-flag | `pyforge.testing_kit.flags` | `src/platform/tests/test_openfeature_file_flags.py`'s hand-written flagd tree |
| branch diff guard (the git mechanics of the fleet's whole-branch diff-guard meta-tests: files and commits changed since `origin/main`, skipping loudly when the base ref is absent) | `pyforge.testing_kit.branch_diff_guard` | the stations' own copies (retro-pyforge-steward-2026-09-04 action item 11) |
| CFE surface (this repository's conda-forge-expert paths, for `unsanctioned_commits`; estate-bound, so it stays A-only) | `pyforge.testing_kit.cfe_surface` | `scripts/mason_cfe_surface_check.py`'s surface (Story 83.19) |

The public surface (every module and public name, the fixtures and markers, the
run-dependencies, the estate-bound members and the Python floor) is written down in
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/contract.md`
(`spec-pyforge-testing-charter` CAP-6); `tests/meta/test_public_contract.py` fails
when the kit and that file differ, so a change to the surface edits both.

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

That task runs the whole suite. It has two halves (`spec-pyforge-testing-charter`
CAP-7): a module that reads the repository outside the kit (the portal-and-CLI
header contract, the lane wiring, the platform flag tree, the contract check)
carries `pytestmark = pytest.mark.live_tree`. The package half runs with no host
package on the path; the live-tree half needs django-pyforge on `PYTHONPATH`:

```bash
pixi run -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests -q -m "not live_tree"
pixi run -e pyforge-testing-kit env PYTHONPATH=src/shared/packages/django-pyforge/src:src/shared/packages/pyforge-core/src \
  pytest src/shared/packages/pyforge-testing-kit/tests -q -m live_tree
```
