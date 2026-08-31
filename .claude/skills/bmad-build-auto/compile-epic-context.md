# Compile Epic Context

**Task**
Given an epic number, the epics file, the planning artifacts directory, and a desired output path, compile a clean, focused, developer-ready context file (`epic-<N>-context.md`).

**Steps**

1. Read the epics file and extract the target epic's title, goal, and list of stories.
2. Scan the planning artifacts directory for the standard files (PRD, architecture, UX/design, product brief).
3. Pull only the information relevant to this epic.
4. Write the compiled context to the exact output path using the format below.

## Exact Output Format

Use these headings:

```markdown
# Epic {N} Context: {Epic Title}

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

{One clear paragraph: what this epic achieves and why it matters.}

## Stories

- Story X.Y: Brief title only
- ...

## Requirements & Constraints

{Relevant functional/non-functional requirements and success criteria for this epic (describe by purpose, not source).}

## Technical Decisions

{Key architecture decisions, constraints, patterns, data models, and conventions relevant to this epic.}

## UX & Interaction Patterns

{Relevant UX flows, interaction patterns, and design constraints (omit section entirely if nothing relevant).}

## Cross-Story Dependencies

{Dependencies between stories in this epic or with other epics/systems (omit if none).}
```

## Rules

- **Scope aggressively.** Include only what a developer working on any story in this epic actually needs. When in doubt, leave it out — the developer can always read the full planning doc.
- **Describe by purpose, not by source.** Write "API responses must include pagination metadata" not "Per PRD section 3.2.1, pagination is required." Planning doc internals will change; the constraint won't.
- **No full copies.** Never quote source documents, section numbers, or paste large blocks verbatim. Always distill.
- **No story-level details.** The story list is for orientation only. Individual story specs handle the details.
- **Nothing derivable from the codebase.** Don't document what a developer can learn by reading the code.
- **Be concise and actionable.** Target 800–1500 tokens total. This file loads into bmad-build-auto's context alongside other material.
- **Never hallucinate content.** If source material doesn't say something, don't invent it.
- **Omit empty sections entirely**, except Goal and Stories, which are always required.

## Freshness (who decides this task runs at all)

Nothing in this file changes with the freshness mechanism: the output path, the exact
headings, the 800–1500 token target, and every rule above are the contract, and they are
identical whether the caller reached this task from a cache miss or from a declared-source
change.

What changed is only the *decision* upstream. `step-01-clarify-and-route.md` item 1.A.2 no
longer guesses validity from "is any file in the planning-artifacts directory newer" — it
asks `marshal context refresh` whether this epic's **declared** planning sources moved. The
declared sources are exactly the documents this task reads: the epics file plus the standard
planning documents (PRD, architecture, UX/design, product brief). Story specs, sprint
ledgers, retros, and research notes are not sources, because this task never reads them — so
one of them landing is no longer a reason to recompile.

When the `derived-context` layer is declared off (the default), the upstream decision falls
back to the previous mtime rule and this task is invoked exactly as often as it was before.

## Error handling

- **If the epics file is missing or the target epic is not found:** write nothing and report the problem to the calling agent. Goal and Stories cannot be populated without a usable epics file.
- **If planning artifacts are missing or empty:** still produce the file with Goal and Stories populated from the epics file. Under Requirements & Constraints, write: "Planning artifacts were unavailable; only epics-file context was used." Never hallucinate content to fill missing sections.
