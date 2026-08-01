# Technical research — BMAD ecosystem live verification (round 1)

> **Scope:** operator-directed deep research (2026-07-31) on everything related to
> BMAD-method, bmad-loop, and the bmad-code-org ecosystem of skills, plugins,
> features and capabilities — the genesis tooling Marshal inits and drives.
> Round 1 = live upstream verification of the chain's time-sensitive claims.
> Feeds: the Marshal brief/PRD refresh (tasks 4–5), the deck family, and the
> `video-scripts` intake. Method: primary sources only (github.com/bmad-code-org,
> docs.bmad-method.org), fetched 2026-07-31/08-01; installed-package ground truth
> from `pixi list` + the env tree. Facts here supersede memory.

## 1. The organization, surveyed (github.com/bmad-code-org, fetched live)

| Repo | Stars | Last update | Note |
|---|---|---|---|
| **BMAD-METHOD** | **51,344** | Aug 1, 2026 | v6 current; **no v7 released**; roadmap names "Skills Architecture, BMad Builder v1, **Dev Loop Automation**" |
| **bmad-loop** | 73 | Aug 1, 2026 | active; latest **release** still v0.9.0 (Jul 21) |
| bmad-manticore | 5 | Jul 27, 2026 | upstream **v3.0.0**, MIT — young but moving fast |
| bmad-module-game-dev-studio | 209 | Jul 18, 2026 | = BMGD |
| bmad-method-test-architecture-enterprise | 87 | Jul 18, 2026 | = TEA (local 1.19.1) |
| **bmad-automator** | 39 | Jul 14, 2026 | **ARCHIVED** — a predecessor automation attempt; loop lineage note |
| bmad-utility-skills | 8 | Jun 28, 2026 | local 2.0.0 |
| **bmad-plugins-marketplace** | 31 | Jun 28, 2026 | the community plugin registry — labs-skills' upstream home |
| bmad-builder | 185 | Jun 22, 2026 | = BMB (local 2.1.0) |
| bmad-method-sample-data | 2 | Jun 9, 2026 | test corpus |

Not visible in the org listing: `bmad-dashboard` / `bmad-method-ui` (the local
`bmad-dashboard` 1.2.2.dev0 is consumed via the staged-recipes#33513 mirror
path, per `docs/specs/bmad-loop-adoption.md` W4 — consistent).

## 2. bmad-loop — pin verification (chain claim: `>=0.9.0,<0.10`)

**The pin is CURRENT.** v0.9.0 (Jul 21) is the latest release; repo activity on
Aug 1 is unreleased work. Release history verified back to v0.7.6, including
the **v0.8.0 BREAKING rename `bmad-auto` → `bmad-loop`**.

**Chain-relevant v0.9.0 contents** (some of our "Marshal gap" premises moved):

- **mid-session token budget guards** — FR-13's premise ("the harness has no
  enforcement") is now *partially* false upstream; Marshal's supervisor remains
  differentiated by being outside the session and un-disableable (NFR-4), but
  the PRD's motivating language should credit the upstream guard and re-scope
  the claim to *external, session-independent* enforcement.
- **graceful stop** — relevant to teardown/liveness design (DW-1-8-6).
- **JSON output for multiple commands** — strengthens the wrap seam (parsing
  surface widens; NFR-9 harness contract tests get cheaper).
- **OpenCode adapter + Windows psmux backend + multiplexer entry points** —
  the portability surface (CAP-6) has more upstream adapters to conform
  against than the chain assumed; psmux weakens the "non-POSIX multiplexer"
  upstream-register entry (FR-58) — verify and update that register item.

## 3. BMAD-METHOD v6 — docs verification (docs.bmad-method.org, dated 2026-08-01)

- **v6 current, no v7 announced.** Roadmap: "Skills Architecture, BMad Builder
  v1, **Dev Loop Automation**, and so much more."
- **The "Dev Loop Automation" roadmap item is strategically load-bearing** for
  the wrap-vs-absorb constraint: upstream intends native loop automation.
  This is not a fork trigger (it's convergence, not stall), but the §5.4
  revisit list should gain a watch item: *upstream ships native loop
  automation overlapping bmad-loop/Marshal supervision* → re-evaluate the
  seam, not the wrap.
- Docs' quick reference lists 11 named workflows; the local install carries
  **51 bmad-* skills** (installed count; the docs undercount because the
  llms-full covers the core path only).
- Local deprecations already tracked (bmad-create-prd/-architecture thin
  wrappers, removed in v7) remain consistent with "no v7 yet".

## 4. bmad-manticore — the video pipeline, verified upstream vs installed

| Fact | Upstream (v3.0.0, MIT) | Installed (2.0.0.dev0 conda) |
|---|---|---|
| Skills | **15** mc-* (mc-ograf absent) | **16** mc-* (incl. `mc-ograf`) — env tree counted |
| Format profiles | **7**: talking-head, screen-tutorial, voiceover-explainer, short, livestream-pack, livestream-vod, course-lesson | per packaged version |
| Gates | 4 hard stops: hook/outline · cut plan · graphics beats · final render | same model |
| Tools orchestrated | HyperFrames (Apache-2.0, local) · Parakeet-MLX/ONNX-ASR (word-level, verbatim fillers) · Kokoro-82M TTS · MusicGen-small · AudioLDM2 · yt-dlp · ffmpeg/node/git/uv | same set |
| Config | `_bmad/custom/config.toml` `[modules.manticore]`; brand at `manticore/brand/` — **tokens.json, production-bible.md, voice-bible.md, blacklist.md, craft-checklist.md, exemplars/, headshots/** | same layout |
| UI rule | "Anything showing a user interface or text that must read correctly comes from real screen recordings, because AI-generated UI renders as convincing-at-a-glance gibberish." (verified verbatim) | same |

**Findings for the video-scripts intake** (`_bmad-output/projects/pyforge-herald/planning-artifacts/intake-video-scripts-manticore-2026-07-31.md`):
- Local package is a major version behind (2.0.0.dev0 vs 3.0.0) — **upgrade
  decision belongs to the spec-video-scripts derivation** (Mason repackages).
- The intake's brand-file list is missing **tokens.json, craft-checklist.md,
  exemplars/, headshots/** — the derivation should add them.
- Two format profiles beyond the intake's four exist (livestream-vod,
  course-lesson) — the livestream non-goal stands, course-lesson may interest
  the operator.
- The "16 mc-* skills" figure in our decks/infographic is **correct for the
  installed package** (derive-from-installed); upstream v3 consolidated to 15.

## 5. Round-1 verdicts against chain claims

| Chain claim | Verdict |
|---|---|
| bmad-loop pinned `>=0.9.0,<0.10` supported range | **HOLDS** — 0.9.0 is latest release |
| "harness has no budget enforcement" (FR-13 motivation) | **RE-SCOPE** — v0.9.0 has in-session guards; Marshal's claim narrows to *external, un-disableable* enforcement |
| FR-58 register: "non-POSIX multiplexer support" upstream gap | **VERIFY/UPDATE** — v0.9.0 shipped a Windows psmux backend |
| Upstream maintenance assumption (Brief A2) | **HOLDS, strongly** — weekly releases, 51k stars on the method |
| Wrap-never-absorb fork triggers | **HOLDS**; add convergence watch item ("Dev Loop Automation" on the method roadmap) |
| manticore facts in decks/intake | **HOLD for installed**; upstream v3 delta recorded above |

## Open for round 2 (queued)

ACP adapter-contract maturity (Q-6 triggers) · OTel `gen_ai.*` stability (Q-5)
· competitive slot re-check (the "every competitor trades away the gate or the
unattendedness" claim in SPEC Why) · bmad-plugins-marketplace inventory ·
bmad-automator post-mortem (why archived — lineage lesson for Marshal).

---

# Round 2 — protocol maturity (Q-5 / Q-6 revisit triggers), fetched 2026-07-31

## 6. ACP (Agent Client Protocol) — Q-6 trigger evaluation

State as of mid-2026 (primary + secondary sources): community-governed at
`github.com/agentclientprotocol`, Apache-2.0, **v0.13.6 (Jun 5, 2026) — still
pre-1.0**; adopted by JetBrains (AI Assistant ships ACP support), Google
(Gemini CLI native), GitHub, and 25+ agents; the **ACP Registry went live
January 2026** (register once, reach every ACP client); Claude Code connects
via an ACP *adapter*, not natively. JSON-RPC 2.0 over stdio, LSP-modeled.
Naming caveat: IBM's unrelated "ACP" merged into A2A and was archived Aug 2025
— 2026 papers still confuse the two.

**Against the Spec's recorded Q-6 triggers** (harness gains an ACP client path
· two must-support adapters ship ACP-only · schema v2 stable with the Claude
adapter's gaps closed): **NONE has fired.** No must-support adapter is
ACP-only; the schema is 0.x; bmad-loop has no ACP client path. **Verdict:
deferral HOLDS — but revisit pressure is materially higher than at chain time**
(registry + JetBrains adoption are the kind of breadth that precedes an
ACP-only adapter appearing). PRD note: keep FR-52's seam cheap; that remains
the hedge.

## 7. OTel `gen_ai.*` — Q-5 verification

**The chain's claim verifies EXACTLY.** The conventions remain **Development
(experimental)**: as of v1.42.0 (Jun 12, 2026) all `gen_ai.*` moved out of the
main semantic-conventions repo into a dedicated `semantic-conventions-genai`
repository — an organizational split for release cadence, **not** a
graduation; no GenAI span/metric/attribute is marked stable as of Jul 17,
2026; `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` governs the
transition; vendors (Datadog, Grafana) support it anyway. **Verdict: Q-5
deferral HOLDS unchanged** — the run journal (FR-18) stays the self-owned
record; revisit on a stable 1.0 cut of the dedicated repo.

## Round-2 verdict table

| Open item | Verdict |
|---|---|
| Q-6 ACP migration triggers | **HOLDS (deferred)** — zero triggers fired; pressure rising; seam stays the hedge |
| Q-5 OTel gen_ai emission | **HOLDS (deferred)** — still Development; June split confirmed as organizational |

Round 3 queued: competitive-slot re-check · bmad-plugins-marketplace inventory
· bmad-automator archive post-mortem · Mary synthesis into market/domain docs.

---

# Round 3 — the competitive slot + lineage, fetched 2026-07-31

## 8. Competitive-slot re-check (SPEC Why claim: "every competitor trades away either the gate or the unattendedness, and nobody treats the spec as an executable contract")

**Verdict: the claim needs NARROWING — the generic half has eroded; the specific half holds.**

The 2026 landscape moved:

- **"Ralph loops" are now a named industry pattern** — unattended overnight
  loops with objective stop criteria (tests pass / completion tag), iteration
  caps, token budgets, stop hooks, and worktree isolation. The practice of
  gated-unattended is mainstream, not our differentiator.
- **Claude Code Auto Mode** (Anthropic, ~May 2026): layered safety — input
  filtering, action evaluation, two-stage classification, human approval
  checkpoints for sensitive ops, and **subagent outbound/return checks**
  (intent alignment + prompt-injection detection on the way back). Gates +
  autonomy in one first-party product — but the safety layer lives IN the
  session/harness, not outside it.
- **Composio AO**: agents in isolated worktrees, each with its own PR; they
  fix CI failures, respond to review comments, and **manage their PR
  lifecycle**; human-on-the-loop milestone gates; CI retries twice then
  escalates. **The closest single competitor** — overlaps CAP-9 (landing) and
  the escalation pattern.
- **Conductor** (macOS): multi-agent parallel worktrees with a review/merge
  dashboard — overlaps CAP-5 (fleet visibility), attended-only.
- **Devin** ($500+/mo, sandboxed delegated worker), **OpenHands** (self-host,
  Docker-centric, regulated/academic adoption), **Copilot Coding Agent**
  (GitHub-native, collaborative-first) — each still trades one side away.
- Calibration data: SWE-bench Verified 20–45%; practitioner-reported 60–80%
  on well-scoped tasks. The "invest in agent infrastructure + tests first"
  consensus IS this factory's thesis, independently converged.

**What remains genuinely unclaimed** (the narrowed slot, for the PRD/Spec Why):

1. **The spec as an executable contract** — five-field kernel + per-story
   intent contracts + **frozen-surface scope checks** at merge. Ralph loops
   stop on tests; nobody else stops on *contract conformance*.
2. **The supervisor OUTSIDE the session** — un-disableable, self-report-blind
   (NFR-4). Auto Mode's safety is in-session; a wedged session is still its
   own witness elsewhere.
3. **Never-false-green as a verdict lattice** — unevaluable ≠ pass, one exit
   authority. No surveyed tool states this property.
4. **The paper trail that survives teardown** — promotion-before-teardown,
   journal-before-the-act. Ralph practice loses exactly this.

Action for task 5 (PRD refresh): re-word the competitive framing from "nobody
combines gates with unattendedness" to the four properties above; add
Composio AO and Auto Mode to the competitive table.

## 9. bmad-automator post-mortem (archived Jul 13, 2026)

Deliberate supersession, not failure: README states the Story Automator "has
been replaced with the newer BMad-Loop — the same functionality, with broader
support, customization, and control." 39 stars, 86 commits, MIT. Lineage:
**bmad-automator → bmad-auto → (v0.8.0 rename) → bmad-loop** — upstream
consolidates automation into ONE maintained engine and retires predecessors
cleanly. Supports wrap-never-absorb: the engine's continuity is actively
managed upstream, and Brief A2 (maintenance) strengthens further.

Sweep remaining: bmad-plugins-marketplace inventory (minor) · Mary synthesis
→ refreshed market-*/domain-* docs (next).
