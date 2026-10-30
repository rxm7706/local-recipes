---
name: scope-slug
# Author instruction (delete it): description is one sentence a teammate can act on. Name the station
# command. Say that the skill runs from the teammate's project directory without a pixi environment
# name. If a pyforge-* package is unpublished, say so.
description: >
  Replace with that one sentence.
---

<!-- Author instructions are comments: the YAML comment in the frontmatter above, and HTML comments like this one
     below it. Lines without a comment are copied as written, with scope, slug and the station name filled in.
     Delete every comment before opening the pull request. -->

# @scope/slug

Marketplace id `scope/slug`. Install this folder into both
`.agents/skills/<name>/` and `.claude/skills/<name>/`.
The human runbook is [steps.md](steps.md); the verified tool versions live
there.

Run from the teammate's project directory.
Do not prefix commands with a pixi environment selector.

## When the station package is installed

```bash
# Replace: the real argv, copied from the station's --help or its engine module
```

## Until that package is published

<!-- Replace this section's body: name the package, the indexes that 404, and the date of the check. If the
     station assembles a published command, give that argv and name the engine by its module
     (pyforge.<station>.engines.<name>), never by a source path. If no published command produces the
     station's report, say that. Do not invent a command. Do not write "this repo". -->

## What this skill is not

<!-- Replace: state the neighbouring skill that owns the work this one must not do. -->
