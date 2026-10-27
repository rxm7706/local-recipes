# Multi-harness matrix — layers, instruments, and binding currency

Companion to `SPEC.md` (spec: marshal-token-economy, living CAP-197 on
`spec-pyforge-marshal`). Each marshal dispatch harness profile (`claude`,
`cursor`, `gemini`, `copilot`, `devin`) crosses the five integration layers
from `integration-layers.md`. Cells name what is **real** for that harness,
the **binding currency** savings roll up in (`core/layer_savings_sources.py`),
and cite **evidence** — never a bare "never" without a probe or an explicit
operator decision.

**Output layer correction (2026-09-16, Story 46.10):** Layer 0 is
**multi-harness**. Caveman ships **21 install targets** (Claude plugin hooks,
Copilot via `npx skills add github-copilot`, Cursor, Gemini via extension
install, Devin terminal, Codex, …). Enforcement strength varies (hooks vs
skill-file conventions); the substrate is the same instrument, not a Claude-only
skill.

## Matrix (packaged harness profiles)

| Harness | Binding currency | output (caveman) | wire (headroom) | structure-graph | derived-context | planning-graph | Notes |
|---|---|---|---|---|---|---|---|
| `claude` | USD (billed tokens; cache-aware) | yes — Genesis deploy + hooks | yes — `[wrapper]` `wrap claude` | yes — codegraph when layer on | yes — build-auto / dispatch | yes — scribe graph retrieve | Full kit when repo defaults apply |
| `copilot` | quota-burn (premium requests) | yes — caveman target `github-copilot` | yes — `[wrapper]` `wrap copilot` (Story 46.10) | yes | yes | yes | Quota failures surface in `session.log`; no pre-flight quota probe |
| `cursor` | quota-burn (subscription) | yes — caveman target `cursor` | **no** — IDE-only wrap (Story 28.29); headless `cursor-agent` | yes | yes | yes | Cursor-first dispatch is deliberate spend avoidance |
| `gemini` | request-count (RPD/TPM) | yes — caveman extension install | **probed, none** — no `wrap gemini` in headroom (2026-10-05) | yes | yes | yes | Turn reduction beats token shaving for this currency |
| `devin` | ACUs | convention only (cloud) | **stub** — no local binary (Story 22.8) | yes | yes | yes | Loud `MRS-DISP-027` absence by design; argv unverified guess |

Layer availability still follows policy: absent `[context]` entries mean off
(CAP-1). Repo defaults (`_bmad-output/policy-defaults.toml`) enable
harness-agnostic layers and `wire = "auto"`, which intersects each profile's
declared `[wrapper]` at launch time (Story 46.4).

## Evidence index

| Claim | Where recorded |
|---|---|
| Copilot headless wrap exists | `headroom wrap copilot --help`; `data/harness_profiles/copilot.toml` `[wrapper]` |
| Cursor wire dead for dispatch | Story 28.29; `cursor.toml` comment; `resolve_wire_wrap` cursor branch |
| Gemini wire absent upstream | `gemini.toml` probe comment (2026-10-05); live `headroom wrap gemini` → no subcommand |
| Devin stub | `devin.toml` `verified = false`; binary not on stack |
| Output multi-harness (21 targets) | Operator adversarial review 2026-09-16; `spec-token-economy-claude-session-path/.memlog.md` |
| Per-harness rollup currency | `HARNESS_CURRENCY` in `core/layer_savings_sources.py` (Story 46.5) |
