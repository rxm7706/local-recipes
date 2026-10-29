# Steps — @scope/slug

<!-- The skeleton the three pilots share; the card renders this file. Author instructions are HTML comments.
     Lines without a comment are copied as written, with the station, tools and dates filled in. Rules:
     one numbered step per action; real commands only; name every unpublished package; do not copy sample
     commands from a paper card. Delete every comment before opening the pull request. -->

Run these from the project you want to <!-- Replace: lock / build / scan -->. Verified <!-- Replace: YYYY-MM-DD -->
against the engine module `pyforge.<station>.engines.<name>` and the tools on the verifying host. Each version
below is what that tool's `--version` printed on that host on that date.

**Before you start.** <!-- Replace: the unpublished pyforge-* packages, the indexes that 404 and the date, and
which numbered steps wait on them. --> Steps 0 and <!-- Replace --> run today.

## 0. Install the published tools

- <!-- Replace: one line per published tool: `tool` version: its PyPI name and its conda-forge name. -->

## 1. <!-- Replace: the station command --> (waits on `pyforge-<station>`)

When `pyforge-<station>` is on your `PATH`:

```bash
# Replace: the station argv
```

## 2. <!-- Replace: the engine the station calls -->

```bash
# Replace: the published argv the engine assembles
```

That is the argv `pyforge.<station>.engines.<name>` assembles. <!-- Replace: each substitution the reader makes. -->

## 3. Stop

<!-- Replace: name the neighbouring skill that owns the next step, and what not to do from here. -->
