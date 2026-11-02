"""Story 15.2 trip fixture for the estate rule ``subprocess-shell-true``.

Never imported or run: opengrep reads it as text. A line ending ``# trips``
must raise a note naming the rule; a line ending ``# safe`` must not.
"""

import subprocess

subprocess.run("ls -l", shell=True)  # trips
subprocess.check_output("echo hi", shell=True)  # trips
subprocess.run(["ls", "-l"])  # safe
subprocess.run(["ls", "-l"], shell=False)  # safe
