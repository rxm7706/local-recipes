# Herald story specs (durable tier)

Per-story intent-contract specs, promoted here after their story merged.

**Why they are tracked.** In a spec-driven build the spec *is* the contract, so it has to
survive worktree teardown and exist in every clone. bmad-loop drafts a story spec into the run's
gitignored `implementation-artifacts/` (runtime scratch); once the story merges, that spec is
copied here and committed. This is the repo-wide convention adopted 2026-07-25 after
pyforge-warden lost 13 of 31 story specs to Tier-3 worktree teardown — see CLAUDE.md
§ *Spec-driven, framework-neutral layout* and `pyforge-warden/planning-artifacts/specs/README.md`.

**What a promoted spec contains.** The frozen `<intent-contract>` (intent, boundaries, I/O and
edge-case matrix), the code map, the task list with acceptance criteria, the review triage log of
every pass, design notes, and the dated verification evidence. It is the record of what was
agreed and what was actually proven — not a narrative of the session.

## Contents

| Spec | Story | Status |
|---|---|---|
| `spec-design-code-bridge/` | The bridge SPEC kernel + `bridge-protocol.md` (pre-story, from the Dream) | reference |
| `spec-1-2-transport-port-primary-mcp-client-adapter-the-transport-spike.md` | 1.2 — `DesignTransport` port + `McpTransport`, the FR-21 prove-or-kill spike | done |

## Known gap

Story 1.1's spec (`spec-1-1-package-scaffold-for-pyforge-herald.md`) has not been promoted yet.
It survives in the primary checkout's gitignored `implementation-artifacts/` — a durability gap,
not an active loss — and is recorded in `deferred-work.md`.
