# Adoption register — every bmad-suite member has a verdict and a wielder

Companion of `spec-bmad-suite-lifecycle` (CAP-1, CAP-3). Measured 2026-09-06 against
`steward suite pipeline-truth` (13/13 recipe = channel = installed), `provision.py`
`_SUPPORTED_MODULES`, and the installed `.claude/skills/` tree. A member's wiring changes only by
changing its row; this table supersedes `spec-bmad-suite-channel-product`'s "never wire-everything"
constraint and closes `one-front-door` row 6.

## 1. Members

| # | Member (version) | Install class | Wired 2026-09-06 | Verdict | Wielder | Provisioning path | Hazards | Status / story |
|---|---|---|---|---|---|---|---|---|
| 1 | `bmad-method` 6.12.0 | installer-tree | present | wield (substrate) | all stations | steward Epic 14 (`upgrade bmad-core`) | installed-stage caveat: pipeline-truth reads conda-meta, not `_bmad/_config/manifest.yaml` | era tail: 30.1–30.5, 14.9 |
| 2 | `bmad-loop` 0.11.1 | runner-home | provisionable | wield | marshal (wrap, never absorb) | `steward provision --runner bmad-loop --env …` | npm-invisible; uv-from-git native path | meta-test 30.4 |
| 3 | `bmad-module-skill-forge` 2.1.0 | own-installer (custom-module registration kept) | present, 16 skills | wield | all stations (domain skills) | `bmad-module-skill-forge install/update`; `--module skf` refused | never `uninstall` (deletes 121 skill dirs); marketplace.json omits `skf-campaign` | pin `v2.1.0` — 46.7 |
| 4 | `bmad-creative-intelligence-suite` 0.3.2 | module | wired (1 revision behind) | wield | herald, scribe | `steward provision --module cis` (idempotent re-provision) | npm stale 0.1.9 vs GitHub 0.3.2 | re-provision — 46.8 |
| 5 | `bmad-eval-quality` 0.2.0.dev0 @3172162f | cli | runnable, no runner | wield (pilot) | warden, marshal (reviewer measurement) | pixi pin; tasks `eval-quality-smoke` / `-review-twin-run` / `-review-replay` | npm 0.1.0 lacks `score`; exact commit pin load-bearing; `__win` variant missing | 45.2 unblocked; mason 14.1 |
| 6 | `bmad-method-test-architecture-enterprise` 1.24.0 | module | unwired | **wield — full adoption** | marshal (workflows, review lens), warden (advisory) | `steward provision --module tea` | replaces `_bmad/scripts/bmad_tea_playwright.py` + 2 meta-tests (equivalence check first) | 46.3, marshal 31.1–31.3, warden 11.2 |
| 7 | `bmad-builder` 2.2.2 | module | unwired | **wield — beside skf** | steward (module/agent authoring), mason | `steward provision --module bmb` | never `--legacy-dir` / `cleanup-legacy.py` (`rmtree` of `_bmad/core/config.yaml`); npm stale 1.1.0 | 46.4 |
| 8 | `bmad-utility-skills` 2.0.0 @HEAD | module | unwired | **wield** | herald, doctor, warden, scribe, marshal, steward (§ 2) | `steward provision --module utility-skills` | no upstream tags; no LICENSE file upstream (recipe vendors MIT text; conda-forge submission held) | 46.2 + station routing stories |
| 9 | `bmad-manticore` 3.1.0.dev0 @c9bcf759 | module (`--custom-source`) | unwired | **wield — Herald studio** | herald | native: `npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-manticore` in the studio root | 3.0 upgrade wipes the studio's `_bmad/` + `_bmad-output/`; G109 renumber (tag 1.0.1 vs 3.1.0.dev0); needs uv, ffmpeg, node, git | 46.6, herald 18.1 |
| 10 | `bmad-labs-skills` 1.0.0.dev0 @HEAD | plugin-path (consent) | documented | **wield — skill-by-skill** | atlas (`mcp-builder`), herald (`slides-generator`), marshal (`multi-repo-git-ops`), steward (`release-please`) | `npx skills add bmad-labs/skills --skill <name>` per consented skill | third-party (thuantan2060); `bmad-skills` on npm is unrelated (bacoco) | 46.5 |
| 11 | `bmad-module-template` 0.1.0 @HEAD | scaffold | n/a | skip (catalog row) | — | none (never provisioned into the tree) | upstream LICENSE is placeholder text | — |
| 12 | `bmad-dashboard` 1.2.2.dev0 | vscode-extension | runnable | wield (opt-in dev surface) | marshal | `bmad-dashboard-install` pixi task | npm `bmad-dashboard` is an unrelated collision; never the console (`retired-console-check`) | — |
| 13 | `mybmad-dashboard` 0.1.0.dev0 | vscode-extension (a Next.js app) | runnable | skip (opt-in operator view only) | — | `mybmad` launcher (feature `bmad-ui`, linux-64) | own Postgres + auth rival `/console/` and OIDC identity | — |

Deprecated (recipes kept as catalog rows, never metapackage run deps): `bmad-method-wds-expansion`
(absorbed into `bmad-ux` at 6.12.0), `bmad-autopilot`, `bmad-dashboard-extension`, `bmalph`.

## 2. Skill routing (CAP-3) — one wielding station per adopted skill

| Skill | Source member | Wielding station | Where the routing note lives | Story |
|---|---|---|---|---|
| `bmad-os-changelog`, `bmad-os-changelog-social` | utility-skills | herald | `bmad-agent-herald` + AGENTS block | herald 18.2 |
| `bmad-os-root-cause-analysis` | utility-skills | doctor | `bmad-agent-doctor` + AGENTS block | doctor 20.4 |
| `bmad-os-review-pr`, `bmad-os-findings-triage` | utility-skills | warden (advisory lens) | `bmad-agent-warden` + AGENTS block | warden 11.1 |
| `bmad-os-diataxis`, `bmad-os-audit-file-refs`, `bmad-os-editorial-review-translation` | utility-skills | scribe | `bmad-agent-scribe` + AGENTS block | scribe 7.1 |
| `bmad-os-gh-triage` | utility-skills | marshal | `bmad-agent-marshal` + AGENTS block | marshal 31.6 |
| `bmad-os-skill-to-bundle` | utility-skills | steward | `bmad-agent-steward` + AGENTS block | 46.2 |
| `bmad-testarch-*` (9 workflows), `tea-test-review` | TEA | marshal (workflows, review lens); warden (advisory) | marshal harness policy; `bmad-agent-warden` | marshal 31.1–31.3, warden 11.2 |
| `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner`, `bmad-bmb-setup` | bmad-builder | steward | `bmad-agent-steward` + AGENTS block | 46.4 |
| `mc-*` (15) | manticore | herald (studio only) | `bmad-agent-herald` | herald 18.1 |
| `mcp-builder` | labs | atlas | `bmad-agent-atlas` | atlas 24.1 |
| `slides-generator` | labs | herald | `bmad-agent-herald` | herald 18.3 |
| `multi-repo-git-ops` | labs | marshal | `bmad-agent-marshal` | marshal 31.6 |
| `release-please` | labs | steward | `bmad-agent-steward` | 46.5 |
| `eval-quality` CLI | eval-quality | warden / marshal | `pilot-contract.md` (spec-bmad-eval-quality) | 45.2 |
| `bmad-cis-*` (10) | CIS | herald, scribe | already routed (`herald-pitch`) | 46.8 |
| `skf-*` (16) | skf | all stations | station skills (spec-29-1, 33-1) | — |

## 3. Posture changes recorded by memlog (2026-09-06)

- `spec-bmad-suite-channel-product` — "wiring is deliberate per-module triage, never
  wire-everything" → "wiring follows the adoption register".
- `spec-bmad-611-era-alignment` — "TEA adoption is optional, not alignment" retired (CAP-13 relay
  to marshal Epic 31); "shims stay through v7 / `bmad-dev-auto` stays" retired (CAP-12, Story 30.5).
- `one-front-door` row 6 ("triage — keep or drop?") — closed: utility-skills, manticore adopted;
  labs by consent; module-template scaffold-only.
