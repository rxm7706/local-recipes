# Regression-harness fixture source (Story 1.3): imports every declared
# dependency so deptry finds zero issues (no DEP002 unused-dependency
# findings) -> the clean fixture stays genuinely clean under the real engine.
import packaging
import requests

__all__ = ["packaging", "requests"]
