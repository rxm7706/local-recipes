# deptry DEP001: totally_absent_pkg_xyz is imported but never declared and
# is not installed -> the high-confidence missing-import finding.
import requests  # declared + imported -> clean
import totally_absent_pkg_xyz  # neither declared nor installed -> DEP001

__all__ = ["requests", "totally_absent_pkg_xyz"]
