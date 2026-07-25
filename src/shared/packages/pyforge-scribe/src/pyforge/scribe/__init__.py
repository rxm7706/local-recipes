"""pyforge.scribe — direct-capture CLI for checked-in team memory.

`scribe capture` writes decisions, ADRs, and project state straight into
`.claude/memory/` (append-only, no clobber). `scribe graph compile` and
`scribe recall` are present as stub subcommands so the CLI's top-level
shape never changes between epics; their real implementation lands in
Epic 2.

The public contract is the `scribe` CLI itself (AD-7) — this package's
`__init__.py` deliberately exports nothing beyond the version, so other
components integrate via the CLI, never by importing internal modules.
"""

__version__ = "0.1.0"
