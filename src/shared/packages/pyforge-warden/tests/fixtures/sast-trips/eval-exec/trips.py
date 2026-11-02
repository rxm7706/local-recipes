"""Story 15.2 trip fixture for the estate rule ``eval-exec``.

Never imported or run: opengrep reads it as text. A line ending ``# trips``
must raise a note naming the rule; a line ending ``# safe`` must not.
"""

import ast

SOURCE = "1 + 1"

eval(SOURCE)  # trips
exec("value = 2")  # trips
ast.literal_eval(SOURCE)  # safe
