"""pyforge.scribe — direct-capture CLI for checked-in team memory.

`scribe capture` writes decisions, ADRs, and project state straight into
`.claude/memory/` (append-only, no clobber). `scribe graph compile` rebuilds
the compiled graph from the named surfaces, and `scribe recall` answers from
that graph alone, with a citation or not at all.

The public contract is the `scribe` CLI itself (AD-7) — this package's
`__init__.py` deliberately exports nothing beyond the version, so other
components integrate via the CLI, never by importing internal modules.
"""

__version__ = "0.1.0"
