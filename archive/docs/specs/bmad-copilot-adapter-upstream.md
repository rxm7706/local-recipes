---
status: superseded
superseded_by: 'superseded 2026-07-25 by the pyforge-marshal planning chain (deferred item, re-owned to Herald for the chat-adapter comms face)'
spec_updated: 2026-07-18
---
> **Note (2026-07-24):** the standalone reference doc `docs/reference/copilot-to-api.md` was removed from the repo. The copilot-api bridge-pattern details now live in the `recipes/copilot-*` / `recipes/litellm-proxy` proxy recipes and their upstream projects; section-specific citations below predate the removal.

# Tech Spec: upstream the `@bmad` Copilot-Chat adapter into the official BMAD VS Code extension

> **Contribution brief.** Unlike most `docs/specs/` intake specs, the implementation target
> is an **upstream repo** (`bmad-code-org/bmad-method-ui`), not this one. This spec is a
> gap analysis + feature brief that can seed either (a) an upstream PR, or (b) a sideloaded
> fork vendored in this repo. It is **not** a `bmad-quick-dev` intake against `local-recipes`.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft** — needs a contribution-path decision (§ Contribution Path) before it can advance |
| Owner | rxm7706 |
| Upstream target | `bmad-code-org/bmad-method-ui` (the repo that ships `bmad-dashboard` + `mybmad`) |
| Prior art | `bmad-code-org/bmad-method-ui#2` — "feat: introduce GitHub Copilot Chat adapter" (OPEN, unmerged) |
| Relationship | Companion to `docs/specs/copilot-bridge-vscode-extension.md` — see § In-IDE vs Headless |

---

## Background

The BMAD project ships two VS Code / web products out of `bmad-method-ui`:

- **`bmad-dashboard`** (the officially released VS Code extension, mirrored in this repo's
  `bmad-ui` env via PR #33513) — a passive **sidebar "real-time GPS"**: sprint-progress %,
  epic cards, active-story tracking, next-action recommendations, Epics/Stories/Kanban
  views, document library, 500 ms file-watching. Workflows are **launched via the
  integrated terminal** only.
- **`mybmad`** — the standalone Next.js web dashboard (project visualization from a repo or
  local folder).

Neither ships a **conversational / Copilot-driven** surface. That capability exists only in
an **unmerged** PR:

**`bmad-method-ui#2` — `bmad-copilot-adapter`** (branch `pi-docket:feat/copilot-bridge`,
still OPEN, 16 commits, CodeRabbit-reviewed). It adds a GitHub **Copilot Chat participant
`@bmad`** with seven slash commands that map chat input to the installer-generated
`.github/prompts` + `.github/agents` artifacts and stream them through **Copilot's own LLM**.
It is a *pure transport/adapter* layer — it never re-implements workflow logic.

Because #2 never merged, the released dashboard has **no** way to *run BMAD agents
conversationally inside Copilot Chat using Copilot as the model backend*. This spec captures
those missing/additive features so they can be contributed into the official extension.

## The gap — what #2 has that the released extension lacks

| Capability | `bmad-dashboard` (released) | `bmad-copilot-adapter` (#2, unmerged) |
|---|---|---|
| Sprint/epic/story visualization | ✅ | ❌ (out of scope for the adapter) |
| File-watching + next-action hints | ✅ | ❌ |
| **`@bmad` Copilot Chat participant** | ❌ | ✅ |
| **`/run <command>` → `.github/prompts` execution** | ❌ | ✅ |
| **Copilot used as the LLM execution backend** | ❌ | ✅ (VS Code Language Model API) |
| **Command discovery in chat** (`/agents`, `/workflows`, `/tasks`) | ❌ | ✅ |
| **`/status` install diagnostics in chat** | partial (sidebar) | ✅ (chat) |
| CLI bridge (bootstrap/status/update) | ❌ | ✅ |

The two products are **complementary, not competing** — the dashboard *shows state*, the
adapter *drives agents*. The ideal shipped product exposes both.

## Features to upstream (from #2)

Sourced from the `bmad-method-ui#2` description; each is additive to `bmad-dashboard`.

- **F-A1 — `@bmad` chat participant.** Register a Copilot Chat participant with the seven
  slash commands: `/run <command>`, `/status`, `/install`, `/update`, `/help`, `/agents`,
  `/workflows`, `/tasks`.
- **F-A2 — Prompt-artifact command registry.** A `CommandRegistry` that scans the CSV
  manifests + `.github/prompts` / `.github/agents` files the BMAD installer emits, so chat
  commands map 1:1 to official prompt definitions (no re-interpretation of workflow logic).
- **F-A3 — ChatBridge (LLM streaming).** Route a chat request to the resolved prompt and
  stream the response through Copilot's model via the **VS Code Language Model API**
  (`vscode.lm`) — Microsoft-sanctioned, TOS-clean, no local proxy.
- **F-A4 — CliBridge.** Child-process spawn + output capture for the commands that shell
  out (bootstrap/status/update), with the security hardening #2 already landed (CSV
  parsing, workspace-root derivation, command-injection guards, UTF-8 BOM handling).
- **F-A5 — Non-invasive install contract.** MUST NOT modify `_bmad/` or overwrite existing
  `.github/` files; pure adapter over installer output (matches #2's v0.2.0 "remove the
  fallback prompt engine" decision).
- **F-A6 — Cross-platform.** PowerShell-friendly commands + cross-platform path handling
  (Windows parity), async-first file I/O to avoid blocking the extension host.

### Additive beyond #2 (this repo's asks)

- **F-A7 — Multiproject awareness.** In a repo using the `_bmad-output/projects/<slug>/`
  multi-project layout, `@bmad` MUST resolve commands against the **active project**
  (`scripts/bmad-switch --current` / the `.active-project` marker) and surface which project
  is active in `/status`. This mirrors the resolver in this repo's `CLAUDE.md`. (Upstream
  BMAD is single-project by default, so this ships as an opt-in that activates only when the
  multi-project markers are present.)
- **F-A8 — Dashboard ↔ chat handoff.** The dashboard's "Next Action" recommendations
  (e.g. "Start Dev Story") become clickable and dispatch `@bmad /run <command>` — closing
  the loop between *seeing* state and *acting* on it.

## Contribution Path (OPEN — decide before advancing past Draft)

Three routes; the choice gates everything else:

1. **Revive & extend `bmad-method-ui#2` upstream.** Pick up the open PR, add F-A7/F-A8, land
   it in the official extension. *Pro:* everyone benefits, TOS-clean, no local maintenance.
   *Con:* depends on upstream maintainer bandwidth; #2 has sat unmerged.
2. **Vendor a sideloaded fork in this repo.** Package the adapter as a sideload-only `.vsix`
   alongside `docs/specs/copilot-bridge-vscode-extension.md`'s extension — same
   consume-not-submit + sideload pattern this repo already uses for
   `bmad-dashboard`/`mybmad-dashboard`. *Pro:* self-serve now. *Con:* fork drift; we carry it.
3. **Both.** Vendor now (route 2) to unblock, and open the upstream PR (route 1) in parallel;
   retire the fork when/if upstream lands.

**Recommendation:** route 3 — vendor to unblock, upstream to make it permanent.

## In-IDE vs Headless — how this relates to the local copilot-bridge

This spec and `docs/specs/copilot-bridge-vscode-extension.md` are the **same idea at two
layers**; they do not overlap:

| | This spec (`@bmad` adapter) | `copilot-bridge-vscode-extension.md` |
|---|---|---|
| Where Copilot is consumed | **Inside** VS Code (Language Model / Chat Participant API) | **Outside** VS Code (`copilot-api` HTTP proxy on `localhost:4141`) |
| Surface bridged | BMAD prompts ↔ Copilot **Chat panel** | Copilot ↔ any **OpenAI/Anthropic-compatible HTTP client** |
| Consumer | A human typing `@bmad /run …` in the IDE | Standalone apps **and headless runners** (`bmad-loop`, `bmad-dev-auto`) |
| TOS posture | Microsoft-sanctioned API — clean | Abuse-detection-sensitive (documented caveat) |

The local bridge spec explicitly excludes the IDE chat panel (its **NG5** / **G6**); this
spec fills exactly that excluded slot. Headless automation (`bmad-loop`/`bmad-dev-auto`)
cannot use the `@bmad` adapter — those runners have no chat panel — so they route through the
HTTP bridge instead (see the copilot-api bridge pattern). Net: **`@bmad` adapter for humans in the IDE; HTTP bridge for headless loops.**

## Open Questions

1. **Contribution path** (§ above) — route 1 / 2 / 3?
2. **Multiproject upstream appetite.** Does the BMAD team want F-A7 in the core extension, or
   should it stay a fork-only extension in this repo?
3. **Model selection.** #2 streams through whatever model Copilot Chat is set to. Should
   `@bmad` pin a model (e.g. force a stronger model for `/run`), or inherit the user's
   Copilot selection? Recommendation: inherit (least surprise), expose an override setting.
4. **Prompt-artifact freshness.** The registry reads installer output; how does it detect a
   stale `.github/prompts` after a `bmad-method` upgrade? (`/status` drift check?)

## References

- **`bmad-code-org/bmad-method-ui#2`** — the prior-art adapter PR (OPEN).
- **`bmad-code-org/bmad-method-ui`** — ships `bmad-dashboard` + `mybmad`.
- **`docs/specs/copilot-bridge-vscode-extension.md`** — the headless/HTTP-bridge companion.
- **the copilot-api bridge pattern** — the bridge-pattern reference + headless-BMAD wiring.
- **VS Code Language Model & Chat Participant API** —
  <https://code.visualstudio.com/api/extension-guides/chat> and
  <https://code.visualstudio.com/api/extension-guides/language-model>.
