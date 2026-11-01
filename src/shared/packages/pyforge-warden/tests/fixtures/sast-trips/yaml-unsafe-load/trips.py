"""Story 15.2 trip fixture for the estate rule ``yaml-unsafe-load``.

Never imported or run: opengrep reads it as text. A line ending ``# trips``
must raise a note naming the rule; a line ending ``# safe`` must not.
"""

import yaml

TEXT = "a: 1"

yaml.load(TEXT, Loader=yaml.Loader)  # trips
yaml.load(TEXT, Loader=yaml.UnsafeLoader)  # trips
yaml.unsafe_load(TEXT)  # trips
yaml.full_load(TEXT)  # trips
yaml.safe_load(TEXT)  # safe
yaml.load(TEXT, Loader=yaml.SafeLoader)  # safe
yaml.load(TEXT, yaml.CSafeLoader)  # safe
