# SelfExplainML conda channel — recipe drop, 2026-07-12

36 packages built from `rxm7706/local-recipes` (branch `claude/bmad-recipes-refresh`),
uploaded to [anaconda.org/SelfExplainML](https://anaconda.org/SelfExplainML), and
verified installable via `mamba create --dry-run -c SelfExplainML -c conda-forge <pkg>`.

```bash
# install any package from the channel
pixi add --channel SelfExplainML --channel conda-forge <package>
# or
mamba install -c SelfExplainML -c conda-forge <package>
```

All builds: rattler-build, linux-64 host (noarch where applicable). Every recipe
carries CFE metadata in-repo; nothing here is submitted to conda-forge unless a
PR is listed.

## BMAD suite (13)

| Package | Version | What it is | Notes |
|---|---|---|---|
| bmad-builder | 2.1.0 | BMAD module builder | bumped 1.6.0→2.1.0; staged-recipes PR #33123 |
| bmad-creative-intelligence-suite | 0.2.1 | CIS module | bumped; PR #33124 |
| bmad-method-wds-expansion | 0.4.3 | Whiteport Design Studio | bumped; PR #33126 |
| bmad-method-test-architecture-enterprise | 1.19.0 | TEA module | bumped; external PR #33292 (consume-not-submit) |
| bmad-story-automator | 1.15.0 | story orchestration skill + helper runtime | bumped + build fixed for upstream restructure; unix-only (`skip: win`); PR #33128 |
| bmad-utility-skills | 2.0.0 | 10 maintainer skills | bumped + v2.0.0 restructure fixes; PR #33129 (license hold) |
| bmad-module-template | 0.1.0 | module scaffold | current; PR #33127 |
| bmalph | 2.11.0 | BMAD phases + Ralph loop CLI | current; PR #33557 |
| bmad-loop | 0.8.1 | deterministic ralph-loop orchestrator (+TUI) | new recipe (GitHub tag; not on npm/PyPI) |
| bmad-labs-skills | 1.0.0.dev0 | community skills marketplace (21 skills) | new; commit-pinned; local-convenience packaging |
| bmad-autopilot | 0.1.0 | community precursor loop w/ PR-lifecycle automation | new; unix-only (`skip: win`) |
| bmad-dashboard | 1.2.2.dev0 | VS Code extension installer | mirror of staged-recipes PR #33513 |
| mybmad-dashboard | 0.1.0.dev0 | Next.js web dashboard + Postgres launcher | mirror of PR #33513; linux/osx only |

## Token / context-optimization tooling (7)

| Package | Version | What it is | Notes |
|---|---|---|---|
| caveman | 1.9.1 | Claude Code token-compression skill (~65% cut) | GitHub tag (npm "caveman" is unrelated); per-arch npm |
| headroom-ai | 0.31.0 | context-optimization layer (lib+CLI, Rust core) | PyPI sdist, maturin; extras not packaged; `ast-grep` substitutes ast-grep-cli |
| rtk | 0.43.0 | Rust Token Killer CLI proxy (60-90% fewer tokens) | cargo build, Apache-2.0 |
| **ccusage** | **19.0.3** | Claude Code usage/cost analyzer | **pinned <20**: v20 npm dist is a shim over prebuilt Bun native binaries that segfault (bun not on conda-forge); 19.0.3 = last pure-JS node-runnable release; broken 20.0.17 uploads removed from channel |
| codegraph | 1.4.1 | pre-indexed code knowledge graph for agents | per-arch (per-platform Bun-compiled natives via npm optionalDeps) |
| claude-mem | 13.10.2 | persistent session memory for agents | npm; LICENSE vendored from repo tag |
| pi-coding-agent | 0.80.6 | badlogic's `pi` coding agent CLI (pi-mono) | @earendil-works npm scope; 17 deps bundled |

## Python apps + prerequisites (7)

| Package | Version | What it is | Notes |
|---|---|---|---|
| pageindex | 0.3.0.dev3 | vectorless reasoning-based RAG tree index | prereq for openkb (exact-pinned upstream) |
| openkb | 0.4.4 | Open LLM Knowledge Base (PageIndex-powered) | upstream `==` pins loosened; markitdown extras expanded |
| langchain-cerebras | 0.8.2 | LangChain Cerebras integration | prereq for codeboarding; python >=3.11,<3.13 |
| trustcall | 0.0.39 | validated/self-correcting tool calling (LangGraph) | pre-existing recipe (staged-recipes PR #33938); uploaded as codeboarding prereq |
| codeboarding | 0.12.5 | interactive architecture diagrams via LLM agents | python 3.12 window; conda name for PyPI "dotenv"→python-dotenv, "docker"→docker-py, tree_sitter (underscore) |
| hermes-agent | 0.18.2 | Nous Research terminal agent (hermes CLI + ACP) | 30 core deps loosened from `==` pins; extras not packaged |
| portalocker | 3.2.0 | file locking library | bumped 2.7.0→3.2.0 (unblocked openkb); 2.7.0 kept for `<2.8` consumers |

## Skills / workflows (4)

| Package | Version | What it is | Notes |
|---|---|---|---|
| andrej-karpathy-skills | 1.0.0.dev0 | Karpathy-derived coding guidelines (CLAUDE.md + skill) | MIT declared but no upstream LICENSE file → vendored, submission hold |
| aidlc-workflows | 2.3.0 | AWS AI-DLC 2.0 (11 agents, 32-stage workflow) | installer for claude/kiro/kiro-ide/codex harnesses; **bun required at runtime (not conda-packaged)** |
| superpowers | 6.1.1 | obra's agentic skills library (TDD, debugging, ...) | skills + hooks + plugin manifest; installer for marketplace-less setups |
| ppt-master | 3.1.0 | PowerPoint-from-SVG-templates Claude skill | bumped 2.3.0→3.1.0; edge-tts omitted (not on conda-forge, narration degrades); ebooklib floor loosened to 0.17 |

## Other tools (5)

| Package | Version | What it is | Notes |
|---|---|---|---|
| pptxgenjs | 4.0.1 | PowerPoint generation JS library | node library (no CLI); use `NODE_PATH=$CONDA_PREFIX/lib/node_modules`; win build branch added (fixes staged-recipes PR #34176 win leg) |
| quarkdown | 2.3.1 | Markdown typesetting (papers/slides/books), JVM | repackaged self-contained release bundles (bundled Java runtime); linux/osx/win sources |
| cdxgen | 12.7.1 | OWASP CycloneDX BOM generator (16 CLIs) | per-arch npm; platform plugin optionals omitted |
| open-code-review | 1.7.7 | Alibaba hybrid code review (`opencodereview`) | Go source build (CGO_ENABLED=0), Apache-2.0 |
| openspec | 1.6.0 | spec-driven development CLI | already on conda-forge (openspec-feedstock); this previews the 0.16.0→1.6.0 bump |

## Assessed but NOT packaged

| Candidate | Verdict |
|---|---|
| WrenAI | blocked — `wrenai` PyPI CLI needs `wren-core-py` + `opendal` (neither on conda-forge; heavy Rust/maturin prereq chain); the stack itself is docker-compose |
| Sync2Jira | blocked — fedmsg / fedora-messaging / webhook-to-fedora-messaging-messages not on conda-forge; deployment-service shape |
| claude-agent-sdk | already on conda-forge at latest (0.2.116) — consume directly |
| bmad-pro-skills | phantom directory listing; no such repo exists |
| bmad-module-game-dev-studio, bmad-method-sample-data | no upstream license — cannot redistribute |
| bmad-manticore | packageable (new official bmad-code-org module, MIT) — offered, not yet requested |
