"""Pin the package version statically so setuptools never loads upstream's
fragile ``_version_helper.py``.

Upstream derives the version dynamically via
``[tool.setuptools.dynamic] version = {attr = "_version_helper.version"}`` +
``[tool.setuptools_scm]``. ``_version_helper.py`` imports private
``setuptools_scm`` internals (``_types``, ``Configuration``, ``fallbacks``,
several ``version`` symbols) that were removed in setuptools_scm 8.x, so the
metadata build fails with ``ImportError: cannot import name '_types'``.

We already know the version (``$PKG_VERSION`` from rattler-build), so we rewrite
pyproject.toml to declare a static ``version`` and drop the dynamic machinery.
Idempotent: a no-op if the version is already static.
"""

import os
import re
import sys

version = os.environ["PKG_VERSION"]
path = "pyproject.toml"

with open(path, encoding="utf-8") as fh:
    text = fh.read()

# Drop `dynamic = ["version"]` (and a `version`-only dynamic list).
text = re.sub(r'(?m)^\s*dynamic\s*=\s*\[\s*"version"\s*\]\s*\n', "", text)

# Drop the `[tool.setuptools.dynamic]` table's version attr line and an empty
# table header left behind.
text = re.sub(
    r'(?m)^\s*version\s*=\s*\{\s*attr\s*=\s*"_version_helper\.version"\s*\}\s*\n',
    "",
    text,
)
text = re.sub(r"(?m)^\[tool\.setuptools\.dynamic\]\s*\n(?=\s*(\[|$))", "", text)

# Drop the `[tool.setuptools_scm]` table (header + any indented body up to the
# next table or EOF).
text = re.sub(
    r"(?ms)^\[tool\.setuptools_scm\]\s*\n(?:(?!^\[).*\n?)*",
    "",
    text,
)

# Inject a static version under [project] if one is not already present.
if not re.search(r"(?m)^\s*version\s*=\s*[\"']", text):
    text = re.sub(
        r"(?m)^(\[project\]\s*\n)",
        r'\1version = "%s"\n' % version,
        text,
        count=1,
    )

with open(path, "w", encoding="utf-8") as fh:
    fh.write(text)

# Sanity: the file must still declare the version and must not reference the
# broken helper.
assert re.search(r"(?m)^\s*version\s*=\s*[\"']%s[\"']" % re.escape(version), text), (
    "static version not written"
)
assert "_version_helper.version" not in text, "dynamic version attr not removed"
print("pin_version.py: pinned version to %s" % version, file=sys.stderr)
