# `.claude/memory/` — Team Memory

## Purpose

Checked-in, version-controlled memory shared by every developer and every
agent session working in this repo — the destination for decisions,
project state, and reference material that would otherwise stay trapped in
one person's user-local auto-memory
(`~/.claude/projects/<encoded-path>/memory/`), invisible to anyone else who
clones the repo. Written with the `scribe` CLI
(`src/shared/packages/pyforge-scribe/`) and loaded into every session via
root `CLAUDE.md`'s `@.claude/memory/MEMORY.md` import.

## Relationship to user-local auto-memory

This layer is **additive and selective**, never a replacement. User-local
auto-memory keeps per-user nuance (tone/terseness preferences, personal
working habits) exactly as it is today. `.claude/memory/` holds only what
would benefit a brand-new contributor on their first session (see
Team-relevance test below) — reusing the same frontmatter schema
byte-compatibly so moving an entry between the two layers is mechanical,
never a translation.

## Schema

Every `.claude/memory/<type>/*.md` file has YAML frontmatter:

```yaml
---
name: kebab-case-slug
description: "One-line description."
metadata:
  type: feedback   # feedback | project | reference
---
```

This is the CURRENT live auto-memory frontmatter shape — `type` **nested**
under a `metadata:` key, not a flat `type:` field — verified against
on-disk auto-memory entries (not just the architecture doc's flatter
shorthand). `pyforge.scribe.models.CaptureRecord` isolates the
(de)serialization of this exact shape in one place
(`to_frontmatter()`/`from_frontmatter()`), so a future upstream schema
change only has to touch that one module.

The body below the frontmatter is free-form markdown. For a direct
`scribe capture` it is the raw `--text` verbatim — no team-voice rewrite,
no `Why:`/`How-to-apply` structuring. A *promoted* entry (`scribe capture
--promote`, Story 1.3) is rewritten in team voice instead; direct capture
is deliberately fast and unstructured.

`type` selects the subdirectory the file lands in: `feedback/`,
`project/`, or `reference/`.

## `MEMORY.md` index

One line per entry, appended under the matching `## Feedback` /
`## Project` / `## Reference` heading:

```markdown
- [slug](type/slug.md) — one-line description
```

Keep `MEMORY.md` under 200 lines — Claude Code truncates context past that
length. There is no automated TTL or decay; see When to prune below.

## Team-relevance test

Before anything lands here, it passes one heuristic: **"Would a
brand-new contributor to this repo, on their first session, without ever
having talked to me, benefit from this rule?"** Yes → belongs in
`.claude/memory/`. No → stays in user-local memory only.

## Promotion workflow (Story 1.3)

`scribe capture --type <type> --text "<text>"` (Story 1.1) is a **direct**
capture — verbatim, at the moment a decision is made, with no scan of
existing memory.

`scribe capture --promote [--source <dir>]` scans a user-local auto-memory
directory (default: Claude Code's per-project
`~/.claude/projects/<encoded-path>/memory/`, derived from the current
working directory; override with `--source` if the auto-detected path is
ever wrong), classifies each entry — `team-relevant` / `personal` /
`already-promoted` / `stale`, against the team-relevance test above —
mechanically rewrites the `team-relevant` ones into team voice (no LLM or
network call: strips first-person "I prefer"/"I want" framing, drops "(the)
user prefers" framing, drops parenthetical asides containing a bare
git-short-hash), and prints the full proposal (target path, rewritten
content, `MEMORY.md` line). Nothing is written until you confirm — decline
and it exits cleanly with zero files changed. The source user-local file is
left byte-for-byte untouched; rewriting it to a pointer stub is Story 1.4.

## Pointer stubs (Story 1.4)

A promoted user-local entry is not deleted — once its content is written
under `.claude/memory/`, the source file is rewritten in place to a pointer
stub: `promoted: true` frontmatter (+ an ISO `promoted_date`) and a
one-line redirect body (`` Promoted to `.claude/memory/<type>/<slug>.md`
on <date>. ``). The original body content is not preserved in user-local
memory after promotion.

Re-running `scribe capture --promote` against the same source directory
classifies any stubbed entry `already-promoted` and skips it — no
re-proposal, no re-write, no duplicate `.claude/memory/` file. Promotion is
therefore safe to re-invoke.

## When to prune

Humans decide. When a rule becomes obsolete (a skill changes, a project
ships or gets retired), edit `MEMORY.md` to remove its index line and
delete or archive the entry file — standard git workflow, no tooling
required.
