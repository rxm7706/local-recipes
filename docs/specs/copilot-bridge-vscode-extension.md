# Tech Spec: `copilot-bridge` VS Code Extension

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bounded scope, single-user feature, ~10–12 implementation stories).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/copilot-bridge-vscode-extension.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Target users | Individual developers on their own Mac or Windows machine |
| Distribution | **Sideloaded `.vsix` only** — never published to the VS Code Marketplace |
| Lifetime | Transitional — see § Lifecycle Expectations |

---

## Background and Context

`docs/copilot-to-api.md` documents a "bridge pattern" that lets an
individual developer use their GitHub Copilot subscription as a stand-in
for direct OpenAI / Anthropic / Gemini API access while procurement of
those keys is in flight. The bridge runs a local proxy (default:
`copilot-api` on `localhost:4141`) and apps point at it via env vars.

Today, setting up the bridge requires the developer to:

1. Read the long `docs/copilot-to-api.md` doc.
2. Install `copilot-api` from conda or `npx`.
3. Run a one-time GitHub OAuth device flow on the CLI.
4. Hand-write a systemd user unit (Mac/Windows: a launchd plist /
   Windows service / Task Scheduler entry — currently undocumented).
5. Set environment variables in their shell for each consumer app.
6. Manually verify with curl.
7. Reverse all of the above when real provider keys arrive.

Every step works, but the friction is real. **This extension wraps that
flow into a self-installable, no-marketplace VS Code extension** so a
developer can sideload one `.vsix`, click "Set up bridge", and be done.

---

## Goals

- **G1.** Provide a single sideloadable `.vsix` (no marketplace listing,
  no publisher account, no telemetry) that installs cleanly on Mac and
  Windows.
- **G2.** Make first-time bridge setup a single command-palette action:
  *"Copilot Bridge: Set Up"*. The wizard handles install, OAuth, service
  registration, and verification.
- **G3.** Surface bridge state (running / stopped / failing) in the
  VS Code status bar so the developer always knows whether their local
  apps will work.
- **G4.** Provide one-click env-var configuration for `presenton`,
  `wuphf`, `tolaria`, and "any OpenAI-compatible app" (writes a
  `.env`-style snippet to clipboard or to a chosen file).
- **G5.** Provide a *Migration Assistant* that walks the developer
  through reverting each app from the bridge to direct provider URLs
  when real keys arrive (per § Migration Path in `docs/copilot-to-api.md`).
- **G6.** Reuse — not replace — the existing IDE Copilot Chat extension.
  The bridge extension is **purely** for the standalone-app side; it
  must not interfere with VS Code's official Copilot integration.

## Non-Goals

- **NG1.** No marketplace publication. Distribution is sideload-only.
- **NG2.** No multi-user / team-shared deployment support. The bridge
  serves one developer on one machine. Team-shared sharing of an
  Individual Copilot subscription is a TOS violation and explicitly
  out of scope (see `docs/copilot-to-api.md` § TOS).
- **NG3.** No telemetry, analytics, error reporting to a remote server,
  or auto-update. The extension is local-first.
- **NG4.** No bundled LLM proxy. The extension *manages* an external
  proxy (`copilot-api` from npm / conda); it does not implement Copilot
  protocol translation itself.
- **NG5.** No support for IDE Copilot Chat features (model selection,
  inline suggestions, etc.). Those remain in the official Copilot
  extensions.
- **NG6.** No JetBrains / PyCharm port in v1. (See § Open Questions —
  may be a v2 scope.)

---

## Lifecycle Expectations

Like the bridge pattern itself, the extension is **transitional**:

- **Install** when provider keys (Anthropic, OpenAI, Gemini) are not yet
  available but apps need to be tested locally.
- **Use** for weeks-to-months while procurement runs.
- **Migrate** apps off the bridge using the extension's Migration
  Assistant once real keys arrive.
- **Uninstall** the extension after the migration soak period.

The extension's UX should make the migration step *more* prominent the
longer it has been running — a soft nudge in the status bar tooltip
("Bridge has been running 47 days — have your provider keys arrived?")
is appropriate.

---

## User Stories

Each story is sized for one BMAD `bmad-create-story` / `bmad-dev-story`
cycle.

### Story 1 — Sideload install path
**As** a developer on Mac or Windows,
**I want** to install the extension from a single `.vsix` file,
**so that** I don't need a marketplace account or admin approvals.

**Acceptance:**
- The repo's CI produces `copilot-bridge-<version>.vsix` on tag.
- `code --install-extension copilot-bridge-<version>.vsix` works on macOS,
  Windows, and Linux without errors.
- Documented install path is published in the extension's README.

### Story 2 — Status-bar indicator
**As** a developer,
**I want** to see whether the bridge proxy is running at a glance,
**so that** I know if my local apps will work right now.

**Acceptance:**
- Status bar item with one of three states: `🟢 Bridge: running`,
  `🔴 Bridge: stopped`, `🟡 Bridge: error (click for details)`.
- Click toggles between Start and Stop when in stable state; opens the
  output panel when in error.
- Polls the proxy's health endpoint every 10 s; backs off to 60 s after
  three consecutive successes.

### Story 3 — Setup wizard
**As** a first-time user,
**I want** a guided setup that handles install + OAuth + service
registration,
**so that** I don't have to read 900 lines of docs to get started.

**Acceptance:**
- Command-palette entry: *Copilot Bridge: Set Up*.
- Wizard checks for Node.js ≥ 20 and offers a doc link if missing.
- Wizard installs `copilot-api` via `npx --yes copilot-api@latest start`
  on first run, OR uses an existing conda-installed binary if found
  (preference: conda-installed → fall back to npx).
- Wizard launches GitHub OAuth device flow; the activation code is
  shown in a notification with a "Copy code & open browser" button.
- Wizard verifies the proxy by hitting `/v1/models`; reports success
  or surfaces the failure mode with a fix hint (network, OAuth, etc.).

### Story 4 — Service registration (cross-platform)
**As** a developer who reboots their machine,
**I want** the bridge to come back automatically,
**so that** I don't have to re-launch it every morning.

**Acceptance:**
- On macOS: registers a `launchd` user agent (`~/Library/LaunchAgents/
  com.local.copilot-bridge.plist`) and enables it.
- On Windows: registers a Task Scheduler entry that runs at user logon
  (preferred) or a portable run-on-startup mechanism (e.g. Startup
  folder shortcut as a fallback).
- On Linux: registers a systemd user unit
  (`~/.config/systemd/user/copilot-bridge.service`), `--user enable`s it.
- "Disable autostart" command reverses each of the above.

### Story 5 — Configuration settings
**As** a developer,
**I want** to change port, rate limit, and bind address from VS Code
settings,
**so that** I don't have to edit unit files by hand.

**Acceptance:**
- Settings exposed under `copilotBridge.*`:
  - `copilotBridge.port` (default 4141)
  - `copilotBridge.rateLimit` (default 60)
  - `copilotBridge.bindAddress` (default `127.0.0.1`; `0.0.0.0` is
    visible but accompanied by a warning about TOS / abuse-detection
    risk if exposed beyond loopback)
  - `copilotBridge.accountType` (`individual` | `business` |
    `enterprise`; default `individual`)
- Changing a setting prompts to restart the proxy.

### Story 6 — One-click app config (`presenton`, `wuphf`, `tolaria`)
**As** a developer,
**I want** a button per app that gives me the right env-var snippet,
**so that** I don't have to look up each app's config convention.

**Acceptance:**
- Command-palette entries:
  - *Copilot Bridge: Configure presenton*
  - *Copilot Bridge: Configure wuphf*
  - *Copilot Bridge: Configure tolaria*
  - *Copilot Bridge: Configure custom OpenAI-compatible app*
  - *Copilot Bridge: Configure custom Anthropic-compatible app*
- Each command opens a quick-pick: "Copy to clipboard" or "Append to
  ~/.bashrc / ~/.zshrc / $PROFILE.ps1".
- The snippet content matches `docs/copilot-to-api.md` § Per-app wiring.

### Story 7 — Smoke-test command
**As** a developer,
**I want** to verify the bridge end-to-end without leaving the IDE,
**so that** I can rule out the bridge before debugging an app.

**Acceptance:**
- Command-palette entry: *Copilot Bridge: Smoke Test*.
- Runs three checks: GET `/v1/models` (OpenAI), POST `/v1/messages`
  with a tiny prompt (Anthropic), and prints output to a dedicated
  output channel "Copilot Bridge".
- Each check shows pass/fail with the response body or error.

### Story 8 — Migration Assistant
**As** a developer who just got a real Anthropic / OpenAI / Gemini key,
**I want** a guided way to switch each app off the bridge,
**so that** I don't forget any consumer or leave a stale `_BASE_URL` in
my shell rc.

**Acceptance:**
- Command-palette entry: *Copilot Bridge: Migrate to Direct Provider*.
- Wizard asks which provider key just arrived (multi-select).
- For each previously-configured app (tracked in extension state), show
  the current bridge config and the proposed direct-provider config.
- Generates a diff per app; supports "apply" or "copy diff to
  clipboard".
- After all apps migrated, offers to disable the proxy autostart but
  *not* delete it (revert path stays open).

### Story 9 — Uninstall / decommission flow
**As** a developer who has soaked direct-provider integration,
**I want** a single command to fully decommission the bridge,
**so that** I don't leave orphaned launchd / systemd / Task Scheduler
entries.

**Acceptance:**
- Command-palette entry: *Copilot Bridge: Decommission*.
- Stops the proxy, disables autostart, deletes the
  launchd/systemd/scheduler entry, and offers (but does not require)
  removing the extension itself and the cached OAuth tokens at
  `~/.local/share/copilot-api/`.

### Story 10 — Privacy + TOS surface
**As** a developer who hasn't read 900 lines of docs,
**I want** the TOS / privacy implications surfaced in the UI,
**so that** I can't silently end up in the abuse-detection danger zone.

**Acceptance:**
- First time the user runs *Set Up*, a modal shows the four-line TOS
  summary (paraphrased from `docs/copilot-to-api.md` § TOS) and
  requires explicit acknowledgement to proceed.
- The acknowledgement is recorded in extension state; subsequent
  setups don't re-prompt for the same major version.
- Bind address `0.0.0.0` triggers a second confirmation: "Exposing
  beyond loopback significantly raises the risk of GitHub
  abuse-detection. Continue?".

### Story 11 — Diagnostic export
**As** a developer asking for help on Discord / GitHub,
**I want** to export a redacted diagnostic bundle,
**so that** I can attach it without manually copying logs.

**Acceptance:**
- Command-palette entry: *Copilot Bridge: Export Diagnostics*.
- Bundles: extension version, VS Code version, OS, proxy version,
  proxy config, last 100 lines of the proxy output channel, and a
  summary of `/v1/models` (model names only, no responses).
- Redacts: OAuth tokens, file paths under `$HOME` (replace with `~`),
  any string starting with `gho_`, `ghp_`, `sk-`, `AIzaSy`.
- Saves to a user-chosen location.

### Story 12 — Repo packaging + CI
**As** the repo maintainer,
**I want** `vsce package` to run in CI and produce an artefact,
**so that** developers can grab the latest `.vsix` from a release page.

**Acceptance:**
- `vscode-extension/copilot-bridge/` directory is added to the repo,
  alongside `recipes/` and `docs/`.
- `package.json` is configured with no publisher (uses placeholder
  `local-only` to satisfy `vsce package` without a marketplace
  account).
- A GitHub Actions workflow builds the `.vsix` on tag and attaches it
  to the GitHub release. Optional — initial implementation can be
  manual `vsce package` until v0.2.

---

## Functional Requirements

### FR-1: Cross-platform proxy lifecycle
- The extension MUST start, stop, and restart the proxy on macOS,
  Windows, and Linux without OS-specific user prompts beyond the
  first-time service-registration permission grant.

### FR-2: No assumed package manager
- The extension MUST work with either:
  - a conda-installed `copilot-api` (preferred when present, since this
    repo ships a recipe for it), OR
  - a `npx`-launched `copilot-api` (no install — fetches on first run).
- It MUST NOT require Homebrew, apt, scoop, or any platform-specific
  package manager.

### FR-3: TOS-acknowledged binding
- The extension MUST default to `127.0.0.1` for the proxy bind
  address. Changing to any non-loopback address MUST trigger an
  additional confirmation modal.

### FR-4: Token storage isolation
- The extension MUST NOT read, copy, or write the OAuth token
  directly. It MUST defer all token handling to `copilot-api` (which
  stores it under `~/.local/share/copilot-api/`).

### FR-5: No telemetry
- The extension MUST NOT make any network call to any host other than
  `localhost:<configured-port>` for proxy health checks.

### FR-6: State persistence
- Extension state (which apps have been configured, ack of TOS modal,
  uptime counters) MUST persist across VS Code restarts using VS Code's
  `globalState` / `workspaceState` APIs (no external file).

---

## Technical Approach

### Stack
- **Language:** TypeScript (standard for VS Code extensions; matches
  the official scaffolding from `yo code`).
- **Build:** `esbuild` or `tsup` (faster than tsc for extension
  bundling).
- **Test:** `@vscode/test-electron` for integration tests, vitest /
  jest for unit tests around the proxy-lifecycle logic.
- **Package:** `@vscode/vsce` (the VS Code Extension CLI). `vsce
  package` produces the `.vsix` without requiring publisher auth.

### File layout (proposed)
```
vscode-extension/copilot-bridge/
├── README.md
├── CHANGELOG.md
├── package.json                ← contributes commands, settings, status-bar
├── package-lock.json
├── tsconfig.json
├── esbuild.config.js
├── src/
│   ├── extension.ts            ← activate(), deactivate()
│   ├── proxy/
│   │   ├── lifecycle.ts        ← start/stop/restart/status
│   │   ├── installer.ts        ← detect conda vs npx; first-run install
│   │   └── health.ts           ← /v1/models polling
│   ├── service/
│   │   ├── launchd.ts          ← macOS plist
│   │   ├── systemd.ts          ← Linux user unit
│   │   └── windows-task.ts     ← Windows Task Scheduler
│   ├── ui/
│   │   ├── statusBar.ts
│   │   ├── setupWizard.ts      ← webview for first-time setup
│   │   ├── migrationWizard.ts
│   │   └── tosModal.ts
│   ├── apps/
│   │   ├── presenton.ts
│   │   ├── wuphf.ts
│   │   ├── tolaria.ts
│   │   └── custom.ts
│   └── diagnostics/
│       └── export.ts
├── resources/
│   ├── icon.png
│   └── walkthrough/            ← VS Code "walkthrough" assets for first-run
└── test/
    ├── unit/
    └── integration/
```

### Key decisions
1. **Spawn vs. service.** The proxy is registered as a user-level
   launchd / systemd / Task Scheduler entry (Story 4) so it survives
   reboots independently of VS Code. The extension *manages* that
   service (start / stop / status) but does not parent it. Developers
   without admin rights on Windows can fall back to a Startup-folder
   shortcut.
2. **Service definitions live in code, not files.** The extension
   generates the `.plist` / `.service` / Task XML at runtime from a
   template parameterised with the user's settings. Avoids drift
   between extension config and on-disk service file.
3. **No webview for the status bar.** Status bar uses native APIs;
   webviews are reserved for the setup wizard (Story 3) and migration
   assistant (Story 8) where multi-step flow benefits from a richer UI.
4. **All long-running operations off the extension host.** Proxy
   processes spawned, never run inside the extension host. Health
   checks are non-blocking `fetch` calls.

### Settings schema (`package.json` excerpt)
```json
"contributes": {
  "configuration": {
    "title": "Copilot Bridge",
    "properties": {
      "copilotBridge.port": { "type": "integer", "default": 4141 },
      "copilotBridge.rateLimit": { "type": "integer", "default": 60 },
      "copilotBridge.bindAddress": {
        "type": "string", "default": "127.0.0.1",
        "enum": ["127.0.0.1", "0.0.0.0"],
        "description": "Bind address. Setting to 0.0.0.0 exposes the proxy beyond loopback and significantly raises GitHub abuse-detection risk."
      },
      "copilotBridge.accountType": {
        "type": "string", "enum": ["individual", "business", "enterprise"],
        "default": "individual"
      },
      "copilotBridge.installSource": {
        "type": "string", "enum": ["auto", "conda", "npx"],
        "default": "auto",
        "description": "Where to source copilot-api from. 'auto' picks conda if installed, falls back to npx."
      },
      "copilotBridge.autostart": { "type": "boolean", "default": true }
    }
  },
  "commands": [
    { "command": "copilotBridge.setup", "title": "Copilot Bridge: Set Up" },
    { "command": "copilotBridge.start", "title": "Copilot Bridge: Start" },
    { "command": "copilotBridge.stop", "title": "Copilot Bridge: Stop" },
    { "command": "copilotBridge.restart", "title": "Copilot Bridge: Restart" },
    { "command": "copilotBridge.smokeTest", "title": "Copilot Bridge: Smoke Test" },
    { "command": "copilotBridge.configurePresenton", "title": "Copilot Bridge: Configure presenton" },
    { "command": "copilotBridge.configureWuphf", "title": "Copilot Bridge: Configure wuphf" },
    { "command": "copilotBridge.configureTolaria", "title": "Copilot Bridge: Configure tolaria" },
    { "command": "copilotBridge.configureCustomOpenAI", "title": "Copilot Bridge: Configure custom OpenAI-compatible app" },
    { "command": "copilotBridge.configureCustomAnthropic", "title": "Copilot Bridge: Configure custom Anthropic-compatible app" },
    { "command": "copilotBridge.migrate", "title": "Copilot Bridge: Migrate to Direct Provider" },
    { "command": "copilotBridge.exportDiagnostics", "title": "Copilot Bridge: Export Diagnostics" },
    { "command": "copilotBridge.decommission", "title": "Copilot Bridge: Decommission" }
  ]
}
```

### Build / package recipe
```bash
cd vscode-extension/copilot-bridge
npm install
npm run build           # esbuild bundle
npx @vscode/vsce package --no-dependencies
# Produces: copilot-bridge-<version>.vsix
```

The `--no-dependencies` flag (or its successor) lets `vsce package`
work without a publisher account — required for sideload-only
distribution.

### Distribution
- The `.vsix` is attached to the repo's GitHub releases.
- A README section documents install:
  ```
  Download copilot-bridge-<version>.vsix from the releases page, then:
    code --install-extension copilot-bridge-<version>.vsix
  ```

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** A developer with no prior knowledge can install the
  `.vsix`, click *Copilot Bridge: Set Up*, complete OAuth, and have a
  working proxy on `localhost:4141` in under five minutes.
- **AC-2.** After a reboot, the bridge is running again without any
  developer action.
- **AC-3.** A developer can configure `presenton`, `wuphf`, and
  `tolaria` via three command-palette actions; each produces a snippet
  that matches `docs/copilot-to-api.md` § Per-app wiring exactly.
- **AC-4.** When the developer obtains a real Anthropic key, the
  Migration Assistant can switch every previously-configured app to
  the direct API in a single workflow.
- **AC-5.** After running *Decommission*, no launchd / systemd / Task
  Scheduler entry related to the bridge remains on the system.
- **AC-6.** The extension never sends a network request to any host
  except `localhost:<port>`.
- **AC-7.** `vsce package` succeeds in CI without a marketplace
  publisher account, producing a `.vsix` that installs on macOS,
  Windows, and Linux.

---

## Open Questions

These are flagged for the BMAD planner agent to elicit answers
before/during implementation.

1. **Conda preference.** When both conda and npx are available, which
   wins by default? Spec says "auto: conda > npx" — confirm with owner.
2. **Windows service mechanism.** Task Scheduler is the cleanest, but
   requires non-trivial COM / `schtasks` manipulation. A simpler
   fallback (`Startup` folder shortcut) is mentioned but loses
   robustness across user-switch scenarios. Pick one as v1 default.
3. **JetBrains / PyCharm parity.** Is a JetBrains Plugin (using the
   IntelliJ Platform SDK) wanted in v1, or strictly v2? PyCharm
   Professional was named in the audience description for the bridge
   doc. Recommendation: defer to v2 (Story 13+ in a future iteration).
4. **Bundled vs. external proxy binary.** Should the `.vsix` ship
   with the `copilot-api` binary embedded (heavier, but works
   offline-after-install) or always pull from npx / conda
   (lighter, requires network on first run)? Recommendation: external
   pull for v1; revisit if air-gapped install is required.
5. **Branding / icon.** Provide an icon, or use a generic one? Branding
   choice is owner-driven.
6. **Test coverage targets.** What's acceptable for v1? Recommendation:
   80% on `proxy/`, `service/`, `apps/`; 50% on `ui/` (UI flows tested
   manually via integration tests).

---

## Dependencies and Constraints

- **D-1.** Requires `copilot-api` upstream to remain functional.
  (Maturity assessment: see `docs/copilot-to-api.md` § Upstream
  Stability Snapshot — "stable but lightly maintained".)
- **D-2.** Requires Node.js 20+ on the developer's machine (VS Code
  extension host runs Node, but `copilot-api` itself needs a runtime).
  Wizard handles detection.
- **D-3.** Requires the developer to have a GitHub Copilot subscription
  (Pro / Business / Enterprise). Wizard does not provision the
  subscription.
- **C-1.** GitHub Copilot TOS — extension MUST surface the TOS modal
  (Story 10) before first run.

---

## Out of Scope (Explicit)

- ❌ Marketplace publication.
- ❌ Multi-user / team-shared deployment.
- ❌ Custom proxy implementation (extension wraps `copilot-api`, doesn't
  reimplement Copilot translation).
- ❌ JetBrains plugin port (v2).
- ❌ Telemetry / analytics / crash reporting.
- ❌ Auto-update mechanism beyond reinstalling a new `.vsix`.
- ❌ Support for the IDE Copilot Chat panel itself.
- ❌ Docker-based proxy deployment (developer-laptop scope only).

---

## References

- **`docs/copilot-to-api.md`** — full bridge-pattern reference; this
  spec implements the developer-experience layer of that doc.
- **`docs/enterprise-deployment.md`** — Artifactory-backed conda channel
  setup (informs the conda-vs-npx choice in Story 3 / FR-2).
- **VS Code extension docs** —
  <https://code.visualstudio.com/api/get-started/your-first-extension>
- **`vsce` CLI** — <https://github.com/microsoft/vscode-vsce>
- **VS Code extension API: status bar, commands, webviews, walkthroughs** —
  <https://code.visualstudio.com/api/references/vscode-api>
- **launchd reference (macOS)** — `man launchd.plist`
- **systemd user units (Linux)** —
  <https://www.freedesktop.org/software/systemd/man/systemd.unit.html>
- **Task Scheduler API (Windows)** —
  <https://learn.microsoft.com/en-us/windows/win32/taskschd/about-the-task-scheduler>

---

## Suggested BMAD Invocation

This spec is structured for `bmad-quick-dev`. Either:

```
# Single shot — let bmad-quick-dev plan + implement story-by-story:
run quick-dev — implement docs/specs/copilot-bridge-vscode-extension.md
```

or, if the team prefers full BMAD Method discipline (PRD →
Architecture → Stories → Implementation):

```
# Phase 2 (Planning) — feed this spec as the brief input:
bmad-create-prd --brief docs/specs/copilot-bridge-vscode-extension.md

# Phase 3 (Solutioning):
bmad-create-architecture
bmad-create-epics-and-stories

# Phase 4 (Implementation):
bmad-sprint-planning
bmad-dev-story        # repeat per story
```

The Quick Flow path is recommended for this scope (12 stories, single
package, well-bounded surface). The full Method path is overkill but
documented for completeness.
