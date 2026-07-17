# Config-precedence fixture source (Story 3.1): imports every declared
# dependency so deptry finds zero issues (no DEP002 unused-dependency
# findings) -- mirrors ../../clean/pkg/__init__.py so the ONLY interesting
# behavior under test is the [tool.pyforge-warden] config layer, not
# unrelated hygiene noise.
import packaging
import requests

__all__ = ["packaging", "requests"]
