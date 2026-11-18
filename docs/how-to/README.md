# How-to Guides

Task-oriented documentation: "how do I do X?" operational instructions.

## Guides

| Guide | Topic |
|-------|-------|
| [`recipe-testing-and-builds.md`](recipe-testing-and-builds.md) | Local builds, `test-recipes.py`, platform matrix, platform CI locally |
| [`github-actions-recipe-ci.md`](github-actions-recipe-ci.md) | On-demand GitHub Actions recipe CI |
| [`pixi-tasks.md`](pixi-tasks.md) | Generated list of every pixi task and the environments that run it |
| [`troubleshooting-recipe-builds.md`](troubleshooting-recipe-builds.md) | Common build failure fixes |
| [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md) | Offline mirror and Artifactory setup (procedural) |
| [`antigravity-developer-startup.md`](antigravity-developer-startup.md) | Antigravity 2.0 developer startup |
| [`manticore-studio.md`](manticore-studio.md) | Herald manticore studio install and render |
| [`driving-a-pyforge-station-backlog.md`](driving-a-pyforge-station-backlog.md) | Dispatching, verifying, and landing BMAD station work |
| [`detect-concurrent-agent-activity.md`](detect-concurrent-agent-activity.md) | Checking for other agents/sessions before you dispatch |
| [`deploy-the-docs-site-to-github-enterprise-pages.md`](deploy-the-docs-site-to-github-enterprise-pages.md) | Internal GitHub Enterprise Pages deploy for the unified docs artifact (`configure-pages` host values + the `pages-site` release zip) |
| [`one-chain-station-ops.md`](one-chain-station-ops.md) | Keep one Dream / Spec / PRD / spine / epic chain per station (lock, rewrite, mop) |
| [`feedstock-failure-remediation.md`](feedstock-failure-remediation.md) | Pointer → Mason skill `mason-feedstock-failure-remediation` (red PR remediation campaign) |
| [`feedstock-platform-expansion.md`](feedstock-platform-expansion.md) | Pointer → Mason skill `mason-feedstock-platform-expansion` (refresh + platform matrix campaign) |
| [`presentation-deck.md`](presentation-deck.md) | Claude Design prototype → self-contained React/Vite slide deck (Marp + PPTX exports) |
| [`run-herald-live-backend-locally.md`](run-herald-live-backend-locally.md) | Loopback platform host, persistent `.herald/herald.db`, and `herald-ship-local` (Story 19.2) |
| [`station-cli-operations.md`](station-cli-operations.md) | Reach every station through the `pyforge <station>` CLI |
| [`reach-a-station-mcp-endpoint.md`](reach-a-station-mcp-endpoint.md) | Call a station's `POST /stations/<station>/mcp` endpoint |
| [`configure-your-coding-agent.md`](configure-your-coding-agent.md) | Make any coding agent load `AGENTS.md` at session start |
| [`launch-a-cost-saving-interactive-session.md`](launch-a-cost-saving-interactive-session.md) | `headroom` and `caveman` in an interactive Claude Code session |
| [`manage-worktrees-with-bmad.md`](manage-worktrees-with-bmad.md) | One worktree per task, landed through a PR |
| [`monitor-the-fleet.md`](monitor-the-fleet.md) | See each station's state, ledgers and blocked work |
| [`troubleshoot-bmad-agent-loops.md`](troubleshoot-bmad-agent-loops.md) | Diagnose and unblock a stuck agent loop |
| [`run-and-understand-detectors.md`](run-and-understand-detectors.md) | Run the detector suite locally and read its results |
| [`reconcile-spec-surface.md`](reconcile-spec-surface.md) | Clear a `spec-surface-check` drift finding |
| [`refresh-the-estate.md`](refresh-the-estate.md) | Refresh library pins and BMAD floors through `steward estate` |
| [`pause-ci.md`](pause-ci.md) | Pause and resume CI surfaces |
| [`track-upstream-todos.md`](track-upstream-todos.md) | Record upstream gaps in `docs/foundry/upstream-todos.yaml` |
| [`purge-preserved-refs.md`](purge-preserved-refs.md) | Operator runbook for removing preserved tags from `origin` |
| [`ai-engine-operations.md`](ai-engine-operations.md) | Run Langflow and DB-GPT beside the platform host |
| [`host-nebari.md`](host-nebari.md) | Bring up a local Nebari cluster on kind with `steward deploy nic` |
| [`ocp-cluster-bringup.md`](ocp-cluster-bringup.md) | Bring up the local OpenShift environment |
| [`disaster-recovery.md`](disaster-recovery.md) | Recovery contract for the platform Helm release |
| [`restore-operations.md`](restore-operations.md) | Restore the platform PostgreSQL database from backups |
| [`adopt-the-operating-model-with-marshal-seed.md`](adopt-the-operating-model-with-marshal-seed.md) | Adopt the operating model in another repository with `marshal seed` |
| [`use-marshal-in-an-air-gapped-site.md`](use-marshal-in-an-air-gapped-site.md) | Use Marshal's seed and substrate bootstrap in an air-gapped site |
| [`run-atlas-pipelines-and-read-datasets.md`](run-atlas-pipelines-and-read-datasets.md) | Run the atlas pipelines and read their datasets |
| [`diagnose-with-doctor.md`](diagnose-with-doctor.md) | Pre-flight check, fleet watch, and reading a doctor prescription |
| [`scan-for-compliance-with-warden.md`](scan-for-compliance-with-warden.md) | Scan a project with warden and read its status and exit code |
| [`record-progress-claims-and-notices-with-herald.md`](record-progress-claims-and-notices-with-herald.md) | Record progress, claims and notices with Herald |
| [`troubleshoot-herald-moments.md`](troubleshoot-herald-moments.md) | Troubleshoot Herald's progress, claims and notices |
| [`schedule-the-scribe-nightly-compile.md`](schedule-the-scribe-nightly-compile.md) | Install and check the Scribe nightly compile trigger |
| [`bootstrap-a-machine-with-steward.md`](bootstrap-a-machine-with-steward.md) | Check prerequisites, set up a checkout and wire the shell with steward |
| [`run-and-read-pr-preflight.md`](run-and-read-pr-preflight.md) | Run the pre-push preflight, choose its scope and catch up on deferred lanes |
| [`upgrade-bmad-core.md`](upgrade-bmad-core.md) | Move BMAD core to a new release without losing local edits |
| [`rotate-platform-secrets.md`](rotate-platform-secrets.md) | Rotate platform secrets and age identities |
| [`use-steward-duties-that-need-operator-consent.md`](use-steward-duties-that-need-operator-consent.md) | Which steward duties an agent plans and an operator runs |
| [`move-vendor-extracts-through-the-corridor.md`](move-vendor-extracts-through-the-corridor.md) | Record a vendor extract, give rows identity and read freshness |
| [`read-steward-registers.md`](read-steward-registers.md) | Read steward's budget, measure, guards and track registers |

See [`docs/MAP.md`](../MAP.md) for the map of every page.
