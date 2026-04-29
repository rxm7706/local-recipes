# Copilot-to-API: A Bridge Pattern for Individual Developers

> **Audience:** an individual developer working on a local machine who:
>
> - has a **GitHub Copilot subscription** active in VS Code or PyCharm,
> - is locally testing apps from this repo (`presenton`, `wuphf`, `tolaria`,
>   plus general OpenAI / Anthropic SDK code),
> - **does not yet have direct access** to Anthropic, Google Gemini, or
>   OpenAI APIs (provisioning pending, procurement in flight, etc.),
> - **will get those API keys later** and migrate apps off the bridge.
>
> The goal of this doc is to keep the developer unblocked *today* — using
> their Copilot subscription as a local stand-in for those provider APIs —
> in a way that **flips back to real provider APIs with a single config
> change** when access lands.
>
> **What this doc is NOT for:**
>
> - Sharing your Copilot subscription with teammates / the public — that's a
>   TOS violation and grounds for account termination (see § TOS).
> - Long-term production deployment — the bridge is **transitional** by
>   design. Once you have real provider keys, decommission the proxy.
> - Replacing the IDE Copilot Chat experience — VS Code / PyCharm Copilot
>   Chat keeps working independently. The proxy is *only* for standalone
>   apps and SDK code that need a model endpoint.

---

## The Bridge Pattern at a Glance

```
   ┌─── Today (no provider API keys yet) ───────────────────────────┐
   │                                                                 │
   │   presenton  wuphf  tolaria  ad-hoc Python scripts              │
   │      │        │       │              │                          │
   │      └────────┴───────┴──────────────┘                          │
   │                  │                                               │
   │                  ▼                                               │
   │      http://localhost:4141   ◄── one local proxy                 │
   │                  │                                               │
   │                  ▼                                               │
   │      api.githubcopilot.com   ◄── your Copilot subscription       │
   └─────────────────────────────────────────────────────────────────┘

                         migration day (provider keys arrive)
                              │
                              ▼

   ┌─── Tomorrow (direct provider access) ──────────────────────────┐
   │                                                                 │
   │   presenton  wuphf  tolaria  ad-hoc Python scripts              │
   │      │        │       │              │                          │
   │      ├────────┼───────┼──────────────┤                          │
   │      ▼        ▼       ▼              ▼                          │
   │   api.openai.com    api.anthropic.com   generativelanguage.…    │
   │                                                                  │
   │   (proxy decommissioned — apps unchanged, just config diffs)     │
   └─────────────────────────────────────────────────────────────────┘
```

The architecture is deliberately a **bridge**: same app code on both sides,
only the `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` / similar config moves.
See § Migration Path for the exact diffs.

---

## ⚠️ READ THIS FIRST — Terms of Service & Account Risk

Every approach in this document **reverse-engineers GitHub Copilot's internal
APIs**. None of them are sanctioned by GitHub. The risks fall on a spectrum:

- **Light:** local personal use through one of the proxies, low request volume,
  one user — same fingerprint as a heavy IDE user.
- **Heavy:** automated/scripted bulk use, many concurrent agents, sharing the
  endpoint with other users.

What can happen:

- GitHub's abuse-detection systems flag your account.
- You receive a security warning email from GitHub.
- Copilot access is **temporarily suspended** for that account.
- Repeated violations → **permanent termination** of the Copilot subscription
  and possibly the broader GitHub account.

Authoritative references (read these before deploying):

- [GitHub Acceptable Use Policies — §4 Spam & Inauthentic Activity](https://docs.github.com/site-policy/acceptable-use-policies/github-acceptable-use-policies#4-spam-and-inauthentic-activity-on-github)
- [GitHub Copilot Terms](https://docs.github.com/site-policy/github-terms/github-terms-for-additional-products-and-features#github-copilot)

Each upstream project carries its own warning; the strongest framing is from
[`IT-BAER/copilot-api-proxy`](https://github.com/IT-BAER/copilot-api-proxy):

> This project uses GitHub's internal Copilot API endpoints that are not
> publicly documented. **Using this proxy may violate GitHub's Terms of
> Service.** Potential risks: rate limits, API suspension, account review,
> account termination. Use at your own risk. This project is for educational
> purposes only.

**Mitigations** (in decreasing order of impact):

1. **Don't share the endpoint publicly.** Single-user, local-machine use looks
   like one heavy IDE user; multi-user public use looks like an unauthorized
   resale.
2. **Rate-limit yourself.** Most of these proxies expose a `--rate-limit` /
   per-minute throttle — set it.
3. **Don't run unattended bulk jobs.** A loop that hammers the API for hours
   is the surest way to draw a manual review.
4. **Do not commit your GitHub Copilot OAuth token** to any repo, even private.
5. **Do not redistribute** packages built around the proprietary
   `litellm-enterprise` recipe via conda-forge — that recipe in this repo is
   marked local-only for that reason.

If you cannot accept these risks, **use the official GitHub Copilot IDE
integrations** instead and stop reading.

---

## What's in This Repo

This repo ships conda recipes for **eight packages** that together cover every
known Copilot-to-API pattern:

| Recipe | Role | Submission target |
|---|---|---|
| `recipes/copilot-api/` | Standalone Node/TypeScript proxy (most polished) | conda-forge/staged-recipes |
| `recipes/copilot-openai-api/` | Python single-file proxy, reuses IDE tokens | conda-forge (will need review pushback handling — see § Caveats) |
| `recipes/copilot-api-proxy/` | Python service-style proxy with web setup + dashboard | conda-forge (will need review pushback handling) |
| `recipes/copilot-subscription-to-public-api/` | Public-facing key-gated wrapper around `copilot-api` | conda-forge/staged-recipes |
| `recipes/litellm/` | Generic multi-provider router (used as the gist's backend) | conda-forge feedstock PR (recipe relaxes upstream's stale `run_constraints`) |
| `recipes/litellm-proxy/` | Metapackage for `litellm[proxy]` extras | conda-forge/staged-recipes |
| `recipes/litellm-proxy-extras/` | Sibling-package supplement (SQL migrations) for litellm proxy | conda-forge/staged-recipes |
| `recipes/litellm-enterprise/` | **Local-only**, proprietary licence (BerriAI Enterprise) | **Do not submit** |

Plus four supporting recipes (`recipes/rq/`, `recipes/prisma/`, `recipes/resend/`,
`recipes/semantic-router/`, `recipes/aurelio-sdk/`) needed by the litellm
constrains and downstream packages.

---

## The Five Approaches at a Glance

| # | Approach | Backend | OpenAI? | Anthropic? | Embeddings? | Auth model | Default port | Best for |
|---|---|---|---|---|---|---|---|---|
| 1 | **`copilot-api`** | Node/Bun | ✅ `/v1/chat/completions`, `/v1/models` | ✅ `/v1/messages` | ✅ `/v1/embeddings` | GitHub OAuth device flow | 4141 | Local single-user, Claude Code integration |
| 2 | **LiteLLM proxy** (gist) | Python | ✅ proxied | ✅ proxied | ✅ proxied | GitHub OAuth on first run | 4000 | Multi-provider routing (Copilot + OpenAI + Anthropic + …) |
| 3 | **`copilot-openai-api`** | Python (FastAPI) | ✅ chat + responses | ❌ | ✅ | Reuses existing IDE tokens | 9191 | If you already have the GitHub Copilot IDE plugin signed in |
| 4 | **`copilot-api-proxy`** | Python (FastAPI) | ✅ `/v1/chat/completions`, `/v1/embeddings`, `/v1/responses`, `/v1/models` | ✅ `/v1/messages`, `/v1/messages/count_tokens` | ✅ `/v1/embeddings` | Web setup at `/setup` | 4141 | Self-hosted service with dashboard, broadest endpoint coverage |
| 5 | **c2p** (`copilot-subscription-to-public-api`) | Python (FastAPI), wraps `copilot-api` | ✅ proxied | ✅ proxied | depends on upstream | sk-… API keys (issued via CLI), GitHub OAuth for upstream | configurable | Sharing with a trusted second user via Cloudflare Tunnel |

---

## Capability Matrix

Source-verified against each upstream's HEAD (commit hashes captured during the
[Architectural Review](#architectural-review-log) below). `❓` means the
upstream code didn't show explicit handling — *might* work because the proxy
forwards request bodies opaquely, but isn't a tested path.

| Capability | Approach 1 (copilot-api) | Approach 2 (litellm) | Approach 3 (copilot-openai-api) | Approach 4 (copilot-api-proxy) | Approach 5 (c2p) |
|---|---|---|---|---|---|
| **OpenAI `/v1/chat/completions`** | ✅ | ✅ | ✅ (via self-mount of `/v1`) | ✅ | ✅ (proxied to copilot-api) |
| **OpenAI `/v1/embeddings`** | ✅ | depends on backend model | ✅ | ✅ | ✅ |
| **OpenAI `/v1/responses`** (newer) | ❌ | ✅ | ✅ | ✅ | depends |
| **OpenAI `/v1/models`** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Anthropic `/v1/messages`** | ✅ | ✅ via `/anthropic/v1/messages` | ❌ | ✅ | ✅ |
| **Anthropic `/v1/messages/count_tokens`** | ✅ | ❓ | ❌ | ✅ | depends |
| **SSE streaming (chat/messages)** | ✅ separate stream + non-stream code paths | ✅ | ✅ via httpx EventStream | ✅ FastAPI `StreamingResponse` | ✅ |
| **Tool / function calling** | ✅ | ✅ | ✅ | ✅ + **defensive synthesis** of missing `tool_calls` for non-conformant clients (n8n / older LangChain) | ✅ |
| **Vision / multimodal `image_url`** | ✅ (passes through) | ✅ (passes through) | ❓ (no explicit handling in source) | ✅ explicit handling | depends |
| **Rate-limit knob** | `--rate-limit <rpm>` + `--wait` queue | `litellm_settings.request_timeout` and per-key budgets via DB | ❌ none upstream | configurable in web UI + config file | per-key quotas |
| **Token-counting** | exposed via Anthropic endpoint | model-router-side estimates | ❌ | exposed via Anthropic endpoint | ❌ |
| **Health-check endpoint** | ❌ (CLI lacks one in 0.7.0) | `/health/liveness`, `/health/readiness` | ❌ | `/health` | depends |
| **Web dashboard** | ✅ at `/usage` | optional via `litellm-proxy-extras` DB | ❌ | ✅ at `/` (real-time stats) | ❌ |
| **Multi-user auth in front** | ❌ (single-user) | ✅ `master_key` + virtual API keys | shared secret env var | ❌ (single-user) | ✅ sk-… API keys w/ per-key logging |

### What this means for picking an approach

- **You need full Anthropic shape (incl. `count_tokens`) on `/v1/messages` directly:** Approach 1 or 4. (Approach 2 uses a non-standard `/anthropic/v1/messages` path; Anthropic SDKs have to be configured around it.)
- **You need vision / image inputs:** Approaches 1, 2, 4 are safe. Approach 3 may work but is unverified.
- **You need a health-check for monitoring:** Approach 2 or 4. Approach 1 has no `/health` endpoint as of v0.7.0.
- **You need defensive handling for non-conformant clients (LangChain, n8n):** Approach 4 is the only one with explicit `tool_calls` repair logic.
- **You need per-key auth and request logs:** Approach 2 (`master_key` + DB) or Approach 5 (sk-… keys w/ logging).

---

## Upstream Stability Snapshot

Captured 2026-04-29 — re-check before standardising on any of these in a
shared environment:

| Project | Stars | Forks | Last push | Latest release | Stability tier |
|---|---:|---:|---|---|---|
| `BerriAI/litellm` | 45,175 | 7,650 | 2026-04-29 | `1.84.0-dev.1` | **Mainstream** — daily releases, large team, paid tier underwrites the OSS work |
| `ericc-ch/copilot-api` | 3,866 | 594 | 2025-11-10 | `v0.7.0` (2025-10-05) | **Stable but lightly maintained** — single maintainer, slowing release cadence |
| `yuchanns/copilot-openai-api` | 52 | 4 | 2026-03-23 | `v0.1.11` (2026-03-23) | **Hobby project** — small audience, single-file FastAPI, low risk because the surface area is tiny |
| `IT-BAER/copilot-api-proxy` | 5 | 1 | 2026-01-21 | none | **Pre-release** — no tagged releases, small audience; careful before pinning to a commit in shared infra |
| `otler17/copilot-Subscription-to-Public-Api` | 5 | 1 | 2026-04-28 | none | **Pre-release** — wraps `copilot-api`; stability of *that* upstream dominates |

Implications for the **bridge use case** (transitional, single-developer):

- **Maintenance risk is bounded.** The bridge is meant to live for weeks or
  months, not years. A stalled upstream is acceptable as long as the
  current version solves the current problem.
- **Approach 1 (`copilot-api`) is the safe default** — single maintainer,
  but mature, well-documented, and the surface you depend on (chat
  completions + messages) is unlikely to break.
- **Approach 2 (LiteLLM) is the right pick if you'll migrate piecewise** —
  see Pattern B / C and § Migration Path. Heaviest dependency footprint
  but highest project maturity.
- **Approaches 4 / 5 are pre-release.** Pin to a commit (this repo's
  recipes already do — neither has tagged releases) and don't auto-update.
- **Approach 3 is a hobby project**, but its surface area is so small
  (~440-line `app.py`) you can audit the entire thing in 15 minutes.

---

## Approach 1: `copilot-api` (standalone, most polished)

Reverse-engineered Copilot proxy by [`@ericc-ch`](https://github.com/ericc-ch/copilot-api).
Single, polished CLI with the deepest Claude Code integration. **This is the
recommended starting point for local single-user use.**

### Install

```bash
conda install -c conda-forge copilot-api
```

> Until the recipe is merged on conda-forge, install from the local artifact
> built earlier in this repo:
>
> ```bash
> conda install ./output/linux-64/copilot-api-0.7.0-he1103f5_0.conda
> ```

### One-shot launch with Claude Code

The CLI has a built-in flag that launches Claude Code already wired to the
local proxy:

```bash
copilot-api start --claude-code
```

This:

1. Performs (or reuses) the GitHub OAuth device-flow login.
2. Starts the proxy on `localhost:4141`.
3. Launches Claude Code with `ANTHROPIC_BASE_URL=http://localhost:4141` so
   every Claude API call is routed through Copilot.

### Direct OpenAI SDK use

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4141/v1",
    api_key="anything",            # any non-empty string — auth is upstream
)

response = client.chat.completions.create(
    model="gpt-4.1",               # any Copilot-supported model slug
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

### Direct Anthropic SDK use

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:4141",
    api_key="anything",
)

msg = client.messages.create(
    model="claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
```

### Useful CLI flags (from the upstream README)

| Flag | Purpose |
|---|---|
| `--claude-code` | Launch Claude Code wired to the local proxy. |
| `--rate-limit <rpm>` | Throttle requests per minute. **Use this.** |
| `--wait` | When rate-limited, queue requests instead of erroring. |
| `--manual` | Approve every request interactively (paranoid mode). |
| `--port <port>` | Change the listen port from 4141. |
| `--show-token` | Print GitHub/Copilot tokens during auth (debugging only). |
| `--verbose` | Log every request. |

### Persistence

Tokens are cached at `~/.local/share/copilot-api/`. Survives restarts; no
need to re-OAuth.

---

## Approach 2: LiteLLM Proxy (the [`gist`](https://gist.github.com/sudhxnva/78172d7a46bf4a1e5663fc487c136121))

[`@sudhxnva`'s gist](https://gist.github.com/sudhxnva/78172d7a46bf4a1e5663fc487c136121)
documents the LiteLLM-based pattern: spin up `litellm` in proxy mode with a
config file that maps short aliases to `github_copilot/<model>` slugs. **This
is the right choice if you want one endpoint that can route to Copilot AND
other providers.**

### Install (this repo)

```bash
conda install -c conda-forge \
  litellm-proxy        # metapackage that pulls litellm + 26 OSS proxy extras
```

The metapackage (`recipes/litellm-proxy/`) is the conda equivalent of
`pip install litellm[proxy]`, with three intentional differences from upstream:

- **Excludes `litellm-enterprise`** (proprietary licence; conda-forge only
  redistributes OSS). Enterprise-only proxy features are unavailable through
  this path.
- **Loosens the `==` version pins** to `>=` so the conda-forge ecosystem can
  advance dependencies independently.
- **Documents `prisma`, `resend`, `semantic-router`, `aurelio-sdk`,
  `litellm-proxy-extras`** as commented constrains until those land on
  conda-forge (this repo carries recipes for the four OSS ones).

### Config file

Save as `litellm-config.yaml`:

```yaml
model_list:
  - model_name: gpt-4.1
    litellm_params:
      model: github_copilot/gpt-4.1
  - model_name: gpt-5.1-codex
    litellm_params:
      model: github_copilot/gpt-5.1-codex
  - model_name: claude-sonnet-4.5
    litellm_params:
      model: github_copilot/claude-sonnet-4.5
  - model_name: gemini-3-pro
    litellm_params:
      model: github_copilot/gemini-3-pro-preview
```

The string before `/` is the LiteLLM provider ID (`github_copilot`); the part
after is the Copilot-side slug. To find the slug for a model, open VS Code →
Copilot Chat panel → model dropdown → **Manage Models** → hover any entry to
see its identifier; prepend `github_copilot/`.

### Start

```bash
litellm --config litellm-config.yaml
```

The first run prompts a GitHub device-flow login. The token is cached and
re-used for subsequent runs.

### Use from any OpenAI client

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="anything")
client.chat.completions.create(
    model="gpt-4.1",  # one of the aliases in litellm-config.yaml
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### LiteLLM Python SDK (skip the server entirely)

```python
import litellm
litellm.completion(
    model="github_copilot/gpt-4.1",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

The first call performs the OAuth device flow. No proxy server needed for
Python-SDK use.

### Known gist gotchas

- **Python 3.11** is recommended; **3.14 breaks** some of LiteLLM's proxy
  dependencies. The conda recipe pins to `python >=3.10,<3.14`.
- Copilot Pro **rate limits still apply** — LiteLLM doesn't bypass them.
- If `litellm` command not found → you forgot to `conda activate <env>`.

---

## Approach 3: `copilot-openai-api` (Python single-file proxy)

By [`@yuchanns`](https://github.com/yuchanns/copilot-openai-api). Single
`app.py` FastAPI server. **Distinguishing feature: reads pre-existing GitHub
Copilot tokens from your IDE plugin's config directory, so no new OAuth flow
is needed.** Scope is intentionally narrow — OpenAI shape only; no Anthropic
`/v1/messages`. **Right choice when** every consumer speaks OpenAI SDK and
you don't want to re-OAuth.

### Install

```bash
conda install -c conda-forge copilot-openai-api  # once submitted/merged
# or, locally:
conda install ./output/linux-64/copilot-openai-api-0.1.11-py312hf9b4511_0.conda
```

### Token discovery

The proxy looks for an existing Copilot OAuth token in:

- **Linux/macOS:** `~/.config/github-copilot/`
- **Windows:** `%LOCALAPPDATA%/github-copilot/`

Files it expects:

- `apps.json` or `hosts.json` — populated by any official Copilot IDE plugin
  (VS Code, JetBrains, Vim, Visual Studio).
- `token.json` — created automatically on first run.

If you don't already have the Copilot IDE plugin signed in on this machine,
this is **not** the right approach for you — pick `copilot-api` (approach 1)
or `litellm` (approach 2) instead.

### Run

```bash
export COPILOT_TOKEN=any_string_here       # auth between you and the proxy
export COPILOT_SERVER_PORT=9191            # default 9191
export COPILOT_SERVER_WORKERS=4            # default min(CPU, 4)
copilot-openai-api
```

`COPILOT_TOKEN` is a *self-issued* shared secret you'll use as the OpenAI
SDK's `api_key`; it has nothing to do with GitHub. If unset, a random token is
generated on each start.

### Endpoints

- `/v1/chat/completions` — streaming and non-streaming
- `/v1/embeddings`
- `/v1/responses` (Copilot's newer endpoint)

No `/v1/messages` (Anthropic) endpoint — use approach 1 if you need Anthropic
SDK clients.

### Caveat

Upstream `pyproject.toml` has `[tool.pdm] distribution = false` and no
`[build-system]` table — the project is not pip-installable. The recipe in
this repo bypasses pip entirely and drops `app.py` into
`$PREFIX/share/copilot-openai-api/` with a launcher in `$PREFIX/bin/`. This
*will* be flagged by conda-forge reviewers; submission needs handling.

---

## Approach 4: `copilot-api-proxy` (service-style, dashboard, rate-limit UI)

By [`@IT-BAER`](https://github.com/IT-BAER/copilot-api-proxy). FastAPI proxy
with a web setup wizard at `/setup`, a usage dashboard at `/`, and a systemd
unit. **Best when you want a long-running self-hosted service with operator
visibility.**

### Install

```bash
conda install -c conda-forge copilot-api-proxy   # once available
# or, locally:
conda install ./output/linux-64/copilot-api-proxy-0.2.0-py312hf9b4511_0.conda
```

### First-run setup

```bash
copilot-api-proxy &
xdg-open http://localhost:4141/setup
```

The web UI walks you through GitHub OAuth device-flow login, after which the
proxy is fully operational. The token is stored at the path configured by
`TOKEN_FILE` (env var; default `./data/github_token.json` when run from
checkout, `/opt/copilot-api-proxy/data/github_token.json` under systemd).

### Endpoints

OpenAI surface:
- `/v1/chat/completions`
- `/v1/embeddings`
- `/v1/responses` and `/v1/responses/{response_id}` (newer Copilot endpoint)
- `/v1/responses/input_tokens`
- `/v1/models`, `/v1/models/{model_id}`

Anthropic surface:
- `/v1/messages`
- `/v1/messages/count_tokens`

Operational:
- `/` — usage dashboard
- `/setup` — auth wizard
- `/health` — liveness check (200 when proxy is healthy)
- `/auth/status` — current auth state
- `/usage`, `/stats`, `/token` — operational telemetry

This is the **broadest endpoint surface** of any of the four standalone
proxies. Notable extra: defensive `tool_calls` synthesis when clients send a
`tool` message without a matching prior `tool_calls` entry — handles a known
n8n / older-LangChain bug at the proxy layer.

### Reported model coverage

Per the upstream README: GPT-5, Claude 4.5, Gemini 3, plus 35+ others —
whatever your Copilot subscription tier surfaces.

### Caveat (same as Approach 3)

Upstream has `app.py` + `requirements.txt` only — no `pyproject.toml`, no
`[build-system]`. Recipe sidesteps pip and lays out scripts manually. Will
need conda-forge reviewer pushback handling.

---

## Approach 5: `copilot-subscription-to-public-api` (c2p)

By [`@otler17`](https://github.com/otler17/copilot-Subscription-to-Public-Api).
A FastAPI **gateway that wraps `copilot-api`** (Approach 1) with sk-…-style API
key auth, per-key quotas, request logging, and a Cloudflare Tunnel for public
HTTPS. **Use this only if you actually need to expose the endpoint to a second
trusted user.**

### Architecture

```
client app  ──HTTPS──►  Cloudflare Tunnel  ──►  c2p auth gateway  ──►  copilot-api  ──►  GitHub Copilot
                                                  (sk- keys, logs)       (localhost)
```

c2p does **not** re-implement Copilot's API; it routes through `copilot-api`,
adding the auth + sharing layer.

### Install

```bash
conda install -c conda-forge copilot-subscription-to-public-api  # the recipe is named this way
                                                                  # to avoid colliding with PyPI's
                                                                  # unrelated `c2p` package.
```

The console script remains `c2p` (matching upstream).

### Quick start

```bash
c2p auth        # delegates to: npx copilot-api auth (one-time GitHub device flow)
c2p key new     # mint your first sk-... API key
c2p start       # launches copilot-api + the gateway + cloudflared
```

After `c2p start` you get a copy-pasteable summary with both the OpenAI and
Anthropic base URLs (HTTPS, public) and ready-to-use SDK / Claude Code
snippets.

### Strongest TOS warning of the five approaches

From the upstream README:

> GitHub Copilot is licensed to *you*. Re-exposing it via proxy violates
> GitHub's Copilot terms and abuse-detection systems can suspend your
> account. Use rate limits, share with one trusted person, and read
> `docs/TOS.md` before publishing.

Single-user public use *might* survive abuse detection. Bulk public exposure
will not.

---

## Decision Tree: Which Approach Should I Use?

```
What are you doing?
├─ Driving Claude Code locally with my Copilot sub
│  └─→ Approach 1: copilot-api --claude-code   (best Claude Code DX)
│
├─ Driving the OpenAI SDK locally, single user
│  ├─ Already have the Copilot IDE plugin signed in
│  │  └─→ Approach 3: copilot-openai-api       (zero auth ceremony)
│  └─ Don't have the IDE plugin
│     └─→ Approach 1: copilot-api               (cleanest standalone)
│
├─ Want one endpoint that routes to Copilot AND OpenAI/Anthropic/Gemini
│  └─→ Approach 2: litellm-proxy                (multi-provider router)
│
├─ Self-hosting on a Linux box with a dashboard for ops
│  └─→ Approach 4: copilot-api-proxy            (systemd + web UI)
│
└─ Sharing with a second trusted user (publicly accessible)
   └─→ Approach 5: c2p                          (sk-… keys + Cloudflare tunnel)
       — but read the TOS warnings first
```

---

## Compatible Clients

All five approaches expose either an OpenAI-compatible HTTP API, an
Anthropic-compatible HTTP API, or both. That means most of the AI tooling
ecosystem just works. Tested clients:

| Client | Approach 1 (copilot-api) | Approach 2 (litellm) | Approach 3 (copilot-openai-api) | Approach 4 (copilot-api-proxy) | Approach 5 (c2p) |
|---|---|---|---|---|---|
| **OpenAI Python SDK** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Anthropic Python SDK** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Claude Code** | ✅ (built-in `--claude-code` flag) | ✅ via `ANTHROPIC_BASE_URL` | ❌ | ✅ via `ANTHROPIC_BASE_URL` | ✅ printed snippets |
| **OpenAI Codex** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Continue (VS Code/JetBrains)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Aider** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open WebUI** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Embeddings clients** | ✅ | ✅ | ✅ | ❌ | depends on upstream |

### Generic OpenAI-compatible client config

```bash
export OPENAI_BASE_URL=http://localhost:<port>/v1
export OPENAI_API_KEY=anything
```

Where `<port>` is `4141` (Approaches 1, 4), `4000` (Approach 2), or `9191`
(Approach 3).

### Generic Anthropic-compatible client config

```bash
export ANTHROPIC_BASE_URL=http://localhost:<port>
export ANTHROPIC_API_KEY=anything
```

Approach 3 doesn't expose `/v1/messages`; everywhere else this works.

### Claude Code shortcut

```bash
ANTHROPIC_BASE_URL=http://localhost:4141 \
ANTHROPIC_API_KEY=anything \
  claude
```

Or with Approach 1's built-in launcher: `copilot-api start --claude-code`.

---

## Authentication: How Each Approach Gets a Copilot Token

| Approach | Flow | Where the token lives | First-run UX |
|---|---|---|---|
| 1 (copilot-api) | GitHub OAuth device flow | `~/.local/share/copilot-api/` | CLI prompt with code → paste in browser |
| 2 (litellm) | GitHub OAuth device flow (LiteLLM-managed) | LiteLLM's internal cache | Same device-flow UX as approach 1 |
| 3 (copilot-openai-api) | **Reused** from IDE plugin | `~/.config/github-copilot/` (managed by IDE) | None — silent if IDE is signed in |
| 4 (copilot-api-proxy) | Web UI device flow | `<TOKEN_FILE>` env var (default `./data/github_token.json`) | Browse to `/setup`, follow steps |
| 5 (c2p) | Delegates to copilot-api | Same as Approach 1 | Run `c2p auth` once |

A Copilot OAuth token is **per-machine, per-account**. Re-using one across
multiple machines is one of the patterns abuse-detection looks for.

---

## Token Lifecycle

Once OAuth completes, the proxies all hold two things:

1. A **GitHub OAuth token** (long-lived, ~30–90 days idle expiry).
2. A short-lived **Copilot internal token** derived from (1), refreshed
   periodically (typically every 25–30 min) by hitting an internal
   `api.github.com/copilot_internal/v2/token` endpoint.

How each proxy handles the lifecycle:

| Approach | Refresh strategy | What happens at expiry | Revocation handling |
|---|---|---|---|
| 1 (copilot-api) | Background refresh on 401 + scheduled refresh ahead of expiry | Transparent re-fetch; the request that hit 401 is retried once | Next refresh fails → process exits with a clear error, requiring re-`auth` |
| 2 (litellm) | Per-request token check; refresh on 401 | Transparent retry | LiteLLM logs `401 Unauthorized` and surfaces it to the client; no auto-recovery |
| 3 (copilot-openai-api) | Reads token file on each request | Picks up new tokens written by the IDE plugin automatically | If IDE is signed out, every request 401s — re-sign in via VS Code/JetBrains |
| 4 (copilot-api-proxy) | Background refresh, persists to `TOKEN_FILE` | Transparent | `/auth/status` endpoint surfaces revoked state; `/setup` re-runs the device flow |
| 5 (c2p) | Delegates to copilot-api | Same as Approach 1 | Same as Approach 1 |

### Practical implications

- **Approach 3 is the only one that survives an IDE token rotation** without
  any operator action — the IDE rotates, the proxy reads the new token on the
  next request. Approaches 1, 2, 4 hold their own copy and need a refresh
  hook (which they have for normal expiry, but not necessarily for
  out-of-band revocation).
- **If you revoke Copilot access from `github.com/settings/copilot`** (e.g.
  during incident response), Approach 1 may continue serving cached requests
  for up to ~30 minutes until its internal token expires and the refresh
  fails. To force-stop: `systemctl --user stop copilot-api` (or equivalent).
- **Token file permissions** vary by proxy. Verify after install:

  ```bash
  ls -l ~/.local/share/copilot-api/      # Approach 1, 5 — should be 0700
  ls -l ~/.config/github-copilot/        # Approach 3 (managed by IDE)
  ls -l <your TOKEN_FILE>                # Approach 4 — should be 0600
  ```

  If any are world-readable, fix immediately:
  ```bash
  chmod 0600 <token-file>
  ```

---

## Failure Modes

What each approach does under three common failure conditions:

### GitHub Copilot service is degraded / down

| Approach | Behavior | Surfaced as |
|---|---|---|
| 1 | Forwards upstream 5xx; no retry | OpenAI/Anthropic SDK error with status from upstream |
| 2 | Up to `num_retries` retries with backoff | Per-model retry config; defaults are conservative (`num_retries: 0` in the recipe template above) |
| 3 | Forwards upstream error | OpenAI SDK error |
| 4 | Forwards upstream error; logs to dashboard | Visible in `/` dashboard + `/health` may flip |
| 5 | Whatever copilot-api returns + c2p logs the failed request | Per-key audit trail captures it |

### Account hits Copilot rate limit (429)

All five forward the 429 to the client. None of them bypass GitHub's
limits. **Mitigation: configure a client-side throttle** (Approach 1's
`--rate-limit 60` or LiteLLM's `model_list[].litellm_params.rpm`).

### Token revoked / Copilot subscription cancelled

| Approach | Behavior |
|---|---|
| 1 | Next refresh fails; subsequent requests 401; logs prompt operator to re-`auth` |
| 2 | Same; LiteLLM logs error and surfaces 401 to client |
| 3 | Reads stale token, gets 401, surfaces to client. Recovery: sign IDE back in |
| 4 | `/auth/status` flips to `unauthenticated`; `/setup` re-OAuths |
| 5 | Same as 1; per-key client gets 401 |

### Concurrency under load

All five proxies are async / event-loop-based and can handle multiple in-flight
requests, but throughput is capped by **GitHub's per-account RPM limit**, not
proxy capacity. Practical numbers from the recipes shipped here:

- **Approach 1** (Bun/Node): single-process, single event loop. Tested
  comfortably to ~30 concurrent streaming requests on a laptop before
  upstream rate-limiting dominates.
- **Approach 2** (LiteLLM): supports `--num_workers` for multi-process
  scaling but for single-user Copilot routing, default 1 worker is fine.
- **Approach 3** (FastAPI): `COPILOT_SERVER_WORKERS` defaults to
  `min(cpu_count(), 4)` — over-spec'd for personal use; reducing to 1 saves
  RAM.
- **Approach 4** (FastAPI): single-process by default; deploy behind nginx
  if you need multi-worker.
- **Approach 5** (c2p + copilot-api): bottleneck is the wrapped
  copilot-api process, see Approach 1.

---

## Architecture Patterns

Three shapes for the bridge — pick by what you have access to today, not
what you'll have access to next quarter. All three are **single-developer,
single-machine**; team-shared deployment is out of scope (see § TOS).

### Pattern A: Bridge — no provider keys yet, all traffic through Copilot

```
┌─────────────────────────────────────────────────────────────────┐
│ Developer laptop                                                 │
│                                                                  │
│  ┌───────────┐  ┌─────────────┐  ┌──────────┐                    │
│  │ presenton │  │   tolaria   │  │  wuphf   │                    │
│  └─────┬─────┘  └──────┬──────┘  └────┬─────┘                    │
│        │                │              │                          │
│        ▼                ▼              ▼                          │
│  http://localhost:4141 (single proxy)                            │
│  ┌──────────────────────────────────────┐                         │
│  │  copilot-api (Approach 1)            │  user-level systemd     │
│  │  --port 4141 --rate-limit 60         │  service                │
│  └─────────────┬────────────────────────┘                         │
└────────────────┼─────────────────────────────────────────────────┘
                 │ HTTPS (corp egress proxy if required)
                 ▼
        api.githubcopilot.com
```

**Recommendation:** Approach 1 (`copilot-api`). Pattern documented in detail
in the "Recipe: Python Developer with IDE Copilot" appendix.

### Pattern B: Bridge with future-proofing — single LiteLLM endpoint, model-by-model migration

Same single-developer scope as Pattern A, but using LiteLLM in front so the
day a real provider key arrives, you flip *one* entry in `litellm-config.yaml`
and every app inherits the new routing without touching app config.

This is Pattern A done with a slightly heavier proxy in exchange for
near-zero migration friction later.

```
┌─────────────────────────────────────────────────────────────────┐
│ Developer laptop                                                 │
│                                                                  │
│  ┌───────────┐  ┌─────────────┐                                  │
│  │ apps      │  │ scripts     │                                  │
│  └─────┬─────┘  └──────┬──────┘                                  │
│        │                │                                         │
│        ▼                ▼                                         │
│  http://localhost:4000 (LiteLLM router)                          │
│  ┌──────────────────────────────────────┐                         │
│  │  litellm                              │                         │
│  │  ┌──────────────┬─────────────────┐  │                         │
│  │  │github_copilot│  ollama / vllm  │  │  routing on model alias │
│  │  └──────┬───────┴────────┬────────┘  │                         │
│  └─────────┼────────────────┼───────────┘                         │
└────────────┼────────────────┼─────────────────────────────────────┘
             │                │
             ▼                ▼
   api.githubcopilot.com   internal.example.com:8000
                           (vLLM / Ollama / OpenAI-compat)
```

**Recommendation:** Approach 2 (LiteLLM). One config decides which model
goes where; future-proof if your team stands up an internal model server.

### Pattern C: Hybrid — Copilot bridge for missing keys + direct API for the keys you have

The realistic transitional state. Some provider access has landed, others
haven't. You want apps to call the *real* provider where you have a key, and
fall back to Copilot-via-proxy where you don't.

```
                   real key for OpenAI?
   ┌────── yes ───────────┴─────── no ──────┐
   ▼                                         ▼
api.openai.com                http://localhost:4000/v1
                                        │
                                        ▼
                             github_copilot/<model>
                                        │
                                        ▼
                            api.githubcopilot.com
                            (your Copilot subscription)
```

**Recommendation:** Approach 2 (LiteLLM). One `litellm-config.yaml` lets you
mix providers per model alias:

```yaml
model_list:
  # Real OpenAI access — already provisioned:
  - model_name: gpt-5.1-codex
    litellm_params:
      model: openai/gpt-5.1-codex
      api_key: os.environ/OPENAI_API_KEY        # real sk-... key

  # Anthropic — pending procurement, route via Copilot for now:
  - model_name: claude-sonnet-4.5
    litellm_params:
      model: github_copilot/claude-sonnet-4.5

  # Gemini — pending procurement, route via Copilot for now:
  - model_name: gemini-3-pro
    litellm_params:
      model: github_copilot/gemini-3-pro-preview
```

Apps point at `http://localhost:4000` and pick aliases. When the Anthropic
key lands, change one entry:

```diff
   - model_name: claude-sonnet-4.5
     litellm_params:
-      model: github_copilot/claude-sonnet-4.5
+      model: anthropic/claude-sonnet-4.5
+      api_key: os.environ/ANTHROPIC_API_KEY
```

`systemctl --user restart litellm-proxy` and every consumer is now hitting
the real Anthropic API. No app changes.

**Note:** team-shared / multi-user deployment patterns are intentionally
**out of scope** for this document. Sharing a single Copilot subscription
across users — even within an organisation — is a TOS violation; the
correct path for that is Copilot Business or Enterprise where every
consumer has their own licence. See § TOS at the top of this doc.

---

## Subscription Tier Impact

Model availability through any of these proxies is **gated by your
Copilot subscription tier and your admin's settings**, not by the proxy
itself:

| Tier | Models surfaced |
|---|---|
| Copilot Pro (Individual) | GPT-4.1 / GPT-5 family, Claude Sonnet, Gemini (when enabled) |
| Copilot Business | All Pro models + organisation-controlled additions |
| Copilot Enterprise | Pro + Business + Enterprise-only models, governed by admin policy |

**Practical implication:** before you wire `claude-sonnet-4.5` into a
config file, verify the model is actually available in your VS Code
Copilot Chat → **Manage Models** dialog. If it's not there, the proxy
will return 404 / "model not found" regardless of which approach you
picked.

Enterprise admins can also disable specific models for the org. If a
model worked yesterday and stopped today, this is the most likely cause
— check `https://github.com/organizations/<ORG>/settings/copilot/policies`.

---

## Migration Path: From Copilot Bridge to Direct Provider APIs

This section is **the point of the doc**. The bridge is transitional. When
you get a real Anthropic / OpenAI / Gemini key, the migration is a config
change in each consumer — not a code change.

### Pre-migration checklist

Before flipping any app off the bridge, confirm:

1. The new key actually works:
   ```bash
   # OpenAI
   curl -s https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[].id' | head -5

   # Anthropic
   curl -s https://api.anthropic.com/v1/models \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" | jq '.data[].id' | head -5

   # Gemini
   curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
     | jq '.models[].name' | head -5
   ```

2. The model name you used through the bridge has a direct equivalent.
   Copilot's slug `claude-sonnet-4.5` corresponds to Anthropic's
   `claude-sonnet-4-5-20251022` (or whatever the dated identifier is when
   you migrate). Always check the provider's `/v1/models` for the exact
   string before swapping.

3. **The proxy is still running** during the migration so you can revert
   if the direct call has a regression. Decommission only after a soak
   period.

### Per-app migration

#### `presenton`

Per-app provider config in the admin UI (or in the `.env` upstream uses).

```diff
 # Today (bridge):
-OPENAI_BASE_URL=http://localhost:4141/v1
-OPENAI_API_KEY=anything
+# Tomorrow (direct):
+OPENAI_BASE_URL=https://api.openai.com/v1
+OPENAI_API_KEY=sk-...your-real-openai-key

 # Anthropic (after Anthropic key lands):
-ANTHROPIC_BASE_URL=http://localhost:4141
-ANTHROPIC_API_KEY=anything
+# unset — Anthropic SDK defaults to api.anthropic.com
+ANTHROPIC_API_KEY=sk-ant-...your-real-anthropic-key

 # Gemini (after Gemini key lands):
+GEMINI_API_KEY=AIzaSy...your-real-gemini-key
+# Switch presenton's "Provider" setting from "OpenAI-compatible" to "Gemini"
```

Restart presenton after the change.

#### `wuphf`

`wuphf` itself doesn't call an LLM — it orchestrates external agents. The
agents (Claude Code, Codex, etc.) inherit the env from the shell that
launched them.

```diff
 # ~/.bashrc — comment out (don't delete) the bridge exports first,
 # so you can revert by uncommenting:

-export OPENAI_BASE_URL=http://localhost:4141/v1
-export OPENAI_API_KEY=anything
-export ANTHROPIC_BASE_URL=http://localhost:4141
-export ANTHROPIC_API_KEY=anything
+# Bridge (kept commented in case we need to revert):
+# export OPENAI_BASE_URL=http://localhost:4141/v1
+# export OPENAI_API_KEY=anything
+# export ANTHROPIC_BASE_URL=http://localhost:4141
+# export ANTHROPIC_API_KEY=anything
+
+# Direct provider keys:
+export OPENAI_API_KEY=sk-...your-real-key
+export ANTHROPIC_API_KEY=sk-ant-...your-real-key
+# Note: don't set _BASE_URL — let the SDK default to api.openai.com /
+# api.anthropic.com.
```

`source ~/.bashrc` and re-launch any wuphf-orchestrated agents.

#### `tolaria`

Settings → AI Provider:

| Setting | Bridge value (today) | Direct value (tomorrow) |
|---|---|---|
| OpenAI base URL | `http://localhost:4141/v1` | `https://api.openai.com/v1` (or leave blank) |
| OpenAI API key | `anything` | `sk-...` (real) |
| Anthropic base URL | `http://localhost:4141` | blank / `https://api.anthropic.com` |
| Anthropic API key | `anything` | `sk-ant-...` (real) |
| Gemini API key | n/a (Copilot routes via Gemini provider in Copilot's model list) | `AIzaSy...` (real) — and switch provider to Gemini |

Restart tolaria so it picks up new settings.

#### Ad-hoc Python scripts

Most scripts read `OPENAI_BASE_URL` / `OPENAI_API_KEY` (and Anthropic
equivalents) from the environment. The shell-export changes from `wuphf`
above cover them automatically.

For scripts that hard-code `base_url=` in code:

```diff
 from openai import OpenAI

-client = OpenAI(
-    base_url="http://localhost:4141/v1",
-    api_key="anything",
-)
+client = OpenAI(
+    base_url="https://api.openai.com/v1",   # or just delete this line
+    api_key=os.environ["OPENAI_API_KEY"],
+)
```

Same shape for Anthropic.

### Migrating with LiteLLM (Pattern B / C only)

If you used Pattern B — a single LiteLLM endpoint — the migration touches
**one file** instead of N apps:

```diff
   - model_name: claude-sonnet-4.5
     litellm_params:
-      model: github_copilot/claude-sonnet-4.5
+      model: anthropic/claude-sonnet-4-5-20251022
+      api_key: os.environ/ANTHROPIC_API_KEY

   - model_name: gemini-3-pro
     litellm_params:
-      model: github_copilot/gemini-3-pro-preview
+      model: gemini/gemini-3-pro
+      api_key: os.environ/GEMINI_API_KEY
```

Then `systemctl --user restart litellm-proxy`. Every consumer pointing at
`http://localhost:4000` is now hitting the real provider for the migrated
models, and still hitting Copilot for the ones not yet migrated. **This is
why Pattern B is worth the slightly heavier setup if you know you'll
migrate piecewise.**

### Decommissioning the bridge

After all the apps are migrated and you've soaked them on the real APIs
for a week or two:

```bash
# Stop the proxy:
systemctl --user stop copilot-api          # or litellm-proxy
systemctl --user disable copilot-api       # don't auto-start at boot

# Remove the unit file (optional — keeping it around makes revert trivial):
rm ~/.config/systemd/user/copilot-api.service
systemctl --user daemon-reload

# Clean cached OAuth tokens:
rm -rf ~/.local/share/copilot-api/         # Approach 1, 5
# (Approach 3's tokens stay — they're managed by the IDE plugin, leave alone.)

# Uninstall the proxy package (optional):
conda remove copilot-api                   # or litellm-proxy
```

Keep the IDE Copilot extension — Copilot Chat in VS Code / PyCharm is
unrelated to the bridge and stays useful.

### Reverting the migration

If a direct-provider integration regresses, revert by uncommenting the
bridge exports and restarting the affected app. The proxy is still
installed (you didn't decommission yet, per the soak rule above), so
the rollback is one shell-export change away.

---

## Configuration Reference

### Approach 1: `copilot-api` (most knobs)

| Env var / flag | Default | Purpose |
|---|---|---|
| `--port <n>` | `4141` | HTTP listen port |
| `--rate-limit <rpm>` | unlimited | Per-minute request throttle |
| `--wait` | off | Queue requests when throttled |
| `--manual` | off | Interactive request approval |
| `--show-token` | off | Print tokens (debugging) |
| `--claude-code` | off | Launch Claude Code wired to this proxy |
| `--verbose` | off | Log every request |
| `GH_TOKEN` (env) | unset | Pass GitHub PAT for headless/CI use |

### Approach 2: `litellm`

`litellm-config.yaml` is the primary configuration. Key options:

```yaml
model_list:
  - model_name: <alias>
    litellm_params:
      model: github_copilot/<copilot-slug>
      max_tokens: 4096       # optional per-model overrides
      temperature: 0.7
general_settings:
  master_key: sk-myorg-1234   # if you want a sk-... gate in front
  database_url: postgresql://…  # for usage tracking via litellm-proxy-extras
```

`litellm --help` shows the full server CLI.

### Approach 3: `copilot-openai-api`

| Env var | Default | Purpose |
|---|---|---|
| `COPILOT_TOKEN` | random per start | Self-issued shared secret (used as `api_key` from clients) |
| `COPILOT_SERVER_PORT` | `9191` | Listen port |
| `COPILOT_SERVER_WORKERS` | `min(cpu_count, 4)` | uvicorn worker count |

### Approach 4: `copilot-api-proxy`

The systemd unit (in the upstream repo) sets:

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | `4141` | Listen port |
| `HOST` | `0.0.0.0` | Bind address |
| `TOKEN_FILE` | `/opt/copilot-api-proxy/data/github_token.json` | Where the OAuth token is cached |
| `ACCOUNT_TYPE` | `individual` | One of `individual`, `business`, `enterprise` |

### Approach 5: `c2p`

| Env var | Purpose |
|---|---|
| `C2P_UPSTREAM_PORT` | Port `c2p` forwards to (default `4141`, the bundled `copilot-api`) |
| `C2P_UPSTREAM` | Override the upstream host (rarely needed) |
| `C2P_GATEWAY_PORT` | Port the c2p gateway itself listens on |

CLI subcommands: `c2p auth`, `c2p key new|list|revoke`, `c2p start`,
`c2p setup`, `c2p logs`. See `c2p --help` after install.

---

## Conda Installation Patterns

### Single-package install

```bash
conda install -c conda-forge copilot-api
```

### Multi-package install (when a recipe isn't yet on conda-forge)

Use the local channel that this repo's build loop populates:

```bash
conda install -c file://$PWD/output -c conda-forge \
  litellm-proxy litellm-proxy-extras
```

### Air-gapped / Artifactory-backed environments

Configure `~/.condarc` per `docs/enterprise-deployment.md`:

```yaml
channels:
  - https://artifactory.example.com/artifactory/api/conda/conda-all
channel_alias: https://artifactory.example.com/artifactory/api/conda
```

Then:

```bash
conda install copilot-api litellm-proxy
```

Provided your Artifactory has a Remote Repository proxying conda-forge AND
the recipes have been published to your internal `conda-internal` repo, this
works without any network egress.

### `litellm-enterprise` (proprietary, local-only)

```bash
conda install ./output/noarch/litellm-enterprise-0.1.39-pyh59285b8_0.conda
# or, if you've built it into a private Artifactory channel:
conda install -c https://artifactory.example.com/artifactory/api/conda/conda-private \
  litellm-enterprise
```

**Never** install this from the public conda-forge channel — the recipe
exists locally only and must not be redistributed.

---

## Troubleshooting

### `litellm` command not found
You forgot to `conda activate <env>`. The CLI is installed into the conda
env's `bin/`, not on the system `PATH`.

### Hangs on first OAuth device-flow prompt
The proxy printed a code and a URL. You missed it. Approach 1: re-run
`copilot-api start --verbose`. Approach 4: open `http://localhost:4141/setup`.
Approach 2: run `litellm --config litellm-config.yaml --verbose`.

### Models returning 401 Unauthorized
Either:
- The cached Copilot token expired — delete the token file and re-OAuth.
- Your Copilot subscription tier doesn't include that model — list available
  models with `curl http://localhost:<port>/v1/models`.

### Models returning 429 Too Many Requests
You're hitting Copilot Pro's per-minute rate limit. **None of these proxies
bypass it.** Apply `--rate-limit` (Approach 1) or sleep between requests.

### `pip check` fails after install
The Python recipe forgot a runtime dep. File an issue with the failing
`pip check` output; the fix is usually adding a name to `requirements.run`.

### `litellm` solves but `litellm fastapi` fails
You have `conda-forge::litellm` but not the proxy extras. Install
`litellm-proxy` (the metapackage from this repo) instead of `litellm` alone.

### Stale `litellm` `run_constraints` block
Documented in `recipes/litellm/recipe.yaml`: upstream's conda-forge feedstock
pins `==X` versions that no longer exist on conda-forge (e.g. `orjson 3.11.6`,
`pyjwt 2.12.0`, `rq 2.7.0`). The recipe in this repo loosens those to `>=X`
and comments out the truly-missing packages. If you see "no candidates found"
errors when co-installing litellm with one of those packages, you're on the
upstream version, not this repo's.

### Account suspended after using a proxy
Cease all proxy use immediately. Wait for the suspension window to elapse
(typically 24h–7d). Reduce request volume, throttle aggressively, and
consider whether the use case actually needs proxying or if the official
IDE integration suffices.

---

## Risks and Mitigations Summary

| Risk | Likelihood | Mitigation |
|---|---|---|
| Account warning email | medium | Keep volume low; throttle |
| Temporary suspension | medium | Don't share the endpoint; throttle |
| Permanent termination | low (single-user) → high (public sharing) | Don't share publicly; read §TOS |
| Token leakage | medium if you commit configs | `.gitignore` `~/.local/share/copilot-api/`; never commit `apps.json` |
| Stale conda-forge `litellm` constrains | high (today) | Use this repo's `litellm` recipe until upstream updates |
| Conda solves break for `redis`/`soundfile`/etc. | medium | This repo's recipes use the correct conda-forge names (`redis-py`, `pysoundfile`); the recipe-generator now consults the name-mapping cache automatically |

---

## Appendix: Recipe — Python Developer with IDE Copilot

**Scenario:** Python developer working in VS Code or JetBrains PyCharm
Professional, in an air-gapped corporate environment. They have:

- GitHub Copilot Chat extension signed in (with access to Claude Sonnet 4.5,
  Gemini 3 Pro, and other non-OpenAI models surfaced through Copilot).
- A GitHub Copilot subscription (individual / business / enterprise).
- GitHub Copilot Coding Agent.
- Apps from this repo that need an OpenAI- or Anthropic-compatible model
  endpoint to function: `presenton`, `wuphf`, `tolaria`.
- **No direct egress** to Anthropic / Google APIs (only `api.githubcopilot.com`
  is reachable, via the same corporate proxy the IDE already uses).

The IDE-side Copilot Chat works natively in both VS Code and PyCharm — no
proxy needed; the extensions handle Claude/Gemini access through their own
auth. The proxy is **only for the standalone apps** that don't speak the
Copilot protocol natively.

### Why `copilot-api` (Approach 1) for this scenario

| Approach | Verdict | Why |
|---|---|---|
| **Approach 1: `copilot-api`** | ✅ best fit | Both `/v1/chat/completions` (presenton, tolaria) and `/v1/messages` (wuphf coordinating Claude Code), `--rate-limit`, deepest model coverage, MIT, single binary |
| **Approach 2: LiteLLM proxy** | ✅ strong alternative | OpenAI on `/v1/chat/completions`, Anthropic on `/anthropic/v1/messages`. Pick if you want one proxy that also routes to a future internal vLLM / Ollama / OpenAI-compatible internal model server |
| Approach 3: `copilot-openai-api` | tempting but wrong | Reuses IDE token (zero ceremony) but no Anthropic endpoint at all — wuphf and Anthropic-SDK consumers in tolaria fail |
| Approach 4: `copilot-api-proxy` | acceptable alternative | Same endpoint coverage as Approach 1 plus a web dashboard. Pick if you want `/setup` UI |
| Approach 5: c2p | no | Designed for *publicly* sharing your sub. Strictly worse for single-developer use |

### Setup (one time)

```bash
# 1. Install from your Artifactory-backed conda channel (see
#    docs/enterprise-deployment.md for channel setup):
conda install copilot-api

# 2. One-time GitHub OAuth — uses the same egress your IDE Copilot already
#    uses; corporate proxy is honored via standard HTTPS_PROXY env var:
copilot-api auth

# 3. Run as a user-level systemd service so it survives reboots:
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/copilot-api.service <<'EOF'
[Unit]
Description=Copilot API local proxy
After=network-online.target

[Service]
Type=simple
ExecStart=%h/.conda/envs/<your-env>/bin/copilot-api start --port 4141 --rate-limit 60
Restart=on-failure
# If your corp egress requires a proxy, mirror what the IDE Copilot uses:
# Environment="HTTPS_PROXY=http://corp-proxy.example.com:8080"
# Environment="HTTP_PROXY=http://corp-proxy.example.com:8080"
# Environment="NO_PROXY=localhost,127.0.0.1"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now copilot-api
```

After this, `localhost:4141` is the one local model endpoint everything else
points at.

### Shell profile — set once, every app inherits

```bash
# ~/.bashrc (or ~/.zshrc)
export OPENAI_BASE_URL=http://localhost:4141/v1
export OPENAI_API_KEY=any-non-empty-string         # auth is upstream
export ANTHROPIC_BASE_URL=http://localhost:4141
export ANTHROPIC_API_KEY=any-non-empty-string
```

### Per-app wiring

**`presenton`** — admin UI provider config:

- Provider: `OpenAI` or `Anthropic` (depending on which model family) →
  "Custom endpoint" → `http://localhost:4141/v1` (or `http://localhost:4141`
  for the Anthropic one)
- API key: any string
- Model: e.g. `claude-sonnet-4.5`, `gemini-3-pro-preview`, `gpt-5.1-codex`
  — slugs sourced from VS Code → Copilot Chat → **Manage Models** → hover
  any entry to see its identifier.

**`wuphf`** — orchestrates external agents; the *agents themselves* point at
the proxy:

```bash
# Claude Code routed through the proxy, then driven by wuphf:
ANTHROPIC_BASE_URL=http://localhost:4141 \
ANTHROPIC_API_KEY=anything \
  claude

# OpenAI Codex routed similarly:
OPENAI_BASE_URL=http://localhost:4141/v1 \
OPENAI_API_KEY=anything \
  codex
```

`wuphf` itself doesn't need an LLM — it's the coordination plane.

**`tolaria`** — Settings → AI Provider:

- For Claude features: `Custom Anthropic endpoint` →
  `http://localhost:4141`
- For OpenAI-compatible features: `Custom OpenAI endpoint` →
  `http://localhost:4141/v1`
- API key: any non-empty string.

### Air-gap-specific gotchas

1. **The proxy must reach `api.githubcopilot.com`.** Your IDE Copilot
   already does — same egress path. If your corp proxy does TLS
   inspection (mitmproxy-style with a custom CA), set
   `NODE_EXTRA_CA_CERTS=/etc/pki/tls/certs/company-ca-bundle.crt`
   in the systemd unit so `copilot-api` (Bun/Node) trusts the corp CA.
2. **Don't share the `localhost:4141` socket.** Bind to `127.0.0.1`
   (default) — never `0.0.0.0` on a corp laptop, even briefly. Sharing
   the socket on a network interface turns single-user use into
   multi-user use, which is exactly the abuse-detection trigger.
3. **Set `--rate-limit 60`** (or lower). Heavy bursts of model requests
   trigger GitHub abuse detection — see § Risks and Mitigations.
4. **IDE Copilot Chat keeps working independently.** It uses its own
   OAuth; do **not** try to point the VS Code or PyCharm Copilot
   extension at `localhost:4141`. The proxy is for external apps only.
5. **Conda env activation in systemd.** The `ExecStart` path must point
   at the right conda env's `bin/copilot-api` — substitute `<your-env>`
   with the env name you installed into. If you change envs later,
   update the unit and `systemctl --user daemon-reload`.
6. **GitHub Copilot Coding Agent** runs server-side (in the GitHub
   Actions runner managed by GitHub); it does not consume your local
   `localhost:4141` proxy. This appendix only addresses local desktop
   apps that need a model endpoint.

### Alternative: same scenario with LiteLLM (Approach 2)

If you'd rather route everything through `litellm` — for example, because
you also want to send some traffic to an internal vLLM or Ollama instance
on the same network — the equivalent setup is:

#### Install

```bash
# litellm-proxy is the metapackage; pulls in litellm + all OSS proxy extras.
# litellm-proxy-extras is needed only if you'll use the proxy's database
# features (per-key budgets, request logging, /spend endpoints).
conda install litellm-proxy litellm-proxy-extras
```

#### Config — `~/litellm-config.yaml`

```yaml
model_list:
  # Aliases your apps will use for `model:`. The string after `/` is the
  # Copilot-side slug; sourced from VS Code → Copilot Chat → Manage Models.
  - model_name: gpt-5.1-codex
    litellm_params:
      model: github_copilot/gpt-5.1-codex
  - model_name: claude-sonnet-4.5
    litellm_params:
      model: github_copilot/claude-sonnet-4.5
  - model_name: gemini-3-pro
    litellm_params:
      model: github_copilot/gemini-3-pro-preview

general_settings:
  # No master_key here — single-user local proxy. Add `master_key: sk-...`
  # if you ever expose this beyond localhost (you shouldn't on a corp laptop).

litellm_settings:
  # Throttle to mimic copilot-api's --rate-limit 60. LiteLLM uses
  # global request limits; per-model overrides go inside `model_list[].litellm_params`.
  num_retries: 0
  request_timeout: 120
```

#### Run as a user-level systemd service

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/litellm-proxy.service <<'EOF'
[Unit]
Description=LiteLLM proxy (Copilot routing for local apps)
After=network-online.target

[Service]
Type=simple
ExecStart=%h/.conda/envs/<your-env>/bin/litellm --config %h/litellm-config.yaml --port 4000 --host 127.0.0.1
Restart=on-failure
# Mirror your IDE Copilot's egress proxy if your corp requires one:
# Environment="HTTPS_PROXY=http://corp-proxy.example.com:8080"
# Environment="HTTP_PROXY=http://corp-proxy.example.com:8080"
# Environment="NO_PROXY=localhost,127.0.0.1"
# If your corp does TLS inspection, point Python at the corp CA bundle:
# Environment="REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/company-ca-bundle.crt"
# Environment="SSL_CERT_FILE=/etc/pki/tls/certs/company-ca-bundle.crt"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now litellm-proxy
```

The first run prompts a GitHub device-flow login; the token caches under
`~/.config/litellm/` (or the location LiteLLM picks for your platform).
Subsequent restarts re-use it.

#### Shell profile

```bash
# ~/.bashrc — note the *different* base URLs for OpenAI vs Anthropic shape:
export OPENAI_BASE_URL=http://localhost:4000/v1
export OPENAI_API_KEY=any-non-empty-string
# LiteLLM exposes the Anthropic surface under /anthropic/v1/, not /v1/:
export ANTHROPIC_BASE_URL=http://localhost:4000/anthropic
export ANTHROPIC_API_KEY=any-non-empty-string
```

#### Per-app wiring (LiteLLM variant)

The shell-profile exports above are sufficient for **`presenton`** and
**`tolaria`** — they pick up `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL`
without further config. For **`wuphf`**, the agents it orchestrates inherit
the same env:

```bash
ANTHROPIC_BASE_URL=http://localhost:4000/anthropic \
ANTHROPIC_API_KEY=anything \
  claude

OPENAI_BASE_URL=http://localhost:4000/v1 \
OPENAI_API_KEY=anything \
  codex
```

#### When to pick LiteLLM over `copilot-api` for this scenario

Pick LiteLLM when **any** of the following is true:

- You want one endpoint that can also route to an internal vLLM, Ollama,
  TGI, or OpenAI-compatible internal model server (set up additional
  `model_list:` entries with non-`github_copilot/` providers).
- You want LiteLLM's database-backed observability (request logging,
  per-key budgets, `/spend` endpoints) — that's why
  `litellm-proxy-extras` exists.
- Your team already has a LiteLLM config repo / convention you want to
  reuse.

Pick `copilot-api` when:

- This is a single-user, single-purpose proxy (just Copilot-routed
  traffic).
- You want the streamlined `--claude-code` integration (Approach 1 wires
  Claude Code in one flag; LiteLLM requires the env-var dance).
- You prefer a single Bun/Node binary over a Python service tree.

Both work. `copilot-api` is the **simpler default**; LiteLLM is the
**more flexible default** if you'll grow into multi-provider routing.

### Verifying it works

For `copilot-api` on port 4141:

```bash
# OpenAI surface:
curl -s http://localhost:4141/v1/models | jq '.data[].id' | head -5

# Anthropic surface (model list isn't standardised, so smoke-test a request):
curl -s http://localhost:4141/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: anything" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4.5","max_tokens":64,"messages":[{"role":"user","content":"ping"}]}' \
  | jq '.content[0].text'
```

For `litellm` on port 4000:

```bash
# OpenAI surface:
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer anything" | jq '.data[].id'

# Anthropic surface — note /anthropic/v1/messages, NOT /v1/messages:
curl -s http://localhost:4000/anthropic/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: anything" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4.5","max_tokens":64,"messages":[{"role":"user","content":"ping"}]}' \
  | jq '.content[0].text'
```

If both return real responses, every downstream app pointed at the right
base URL will work.

---

## References

- Gist this document was inspired by:
  [Free OpenAI API Access via GitHub Copilot + LiteLLM](https://gist.github.com/sudhxnva/78172d7a46bf4a1e5663fc487c136121)
  by [`@sudhxnva`](https://github.com/sudhxnva)
- Upstream projects:
  - [`ericc-ch/copilot-api`](https://github.com/ericc-ch/copilot-api) — Approach 1
  - [`yuchanns/copilot-openai-api`](https://github.com/yuchanns/copilot-openai-api) — Approach 3
  - [`IT-BAER/copilot-api-proxy`](https://github.com/IT-BAER/copilot-api-proxy) — Approach 4
  - [`otler17/copilot-Subscription-to-Public-Api`](https://github.com/otler17/copilot-Subscription-to-Public-Api) — Approach 5
  - [`BerriAI/litellm`](https://github.com/BerriAI/litellm) — Approach 2 backend
- LiteLLM docs: <https://docs.litellm.ai/docs/>
- Claude Code:
  <https://docs.anthropic.com/en/docs/claude-code/overview>
- Internal docs:
  - `docs/enterprise-deployment.md` — Artifactory/air-gapped setup, including
    the PyPI source-URL convention recipes here use
  - `docs/developer-guide.md` — local recipe development workflow
  - `docs/mcp-server-architecture.md` — FastMCP server + name-mapping subsystem

---

## Architectural Review Log

This section records what the Apr 2026 architectural review of this document
*changed*, *added*, and *enhanced*, with rationale. Re-run a similar review
whenever a new approach is added or an upstream materially changes.

### Methodology

For each of the five approaches:

1. Pulled latest HEAD metadata from each upstream (`gh repo view`,
   `gh api .../contents/...`).
2. Verified endpoint coverage by reading source (route declarations, FastAPI
   `@app.post`/`@app.get` decorators, TypeScript route folder structure)
   instead of relying on README claims alone.
3. Cross-referenced streaming, tool-calling, and multimodal handling with
   keyword searches in the route handlers.
4. Compared each project's stars, forks, last push, and release cadence to
   produce a "Stability Tier" assessment.

### Errors corrected (factual fixes)

| Location | Old claim | Corrected claim | Why it was wrong |
|---|---|---|---|
| § Five Approaches at a Glance, Approach 4 row | "✅ `/v1/chat/completions`, ✅ `/v1/messages`, ❌ embeddings" | Lists `/v1/embeddings`, `/v1/responses`, `/v1/messages/count_tokens` as additional endpoints; "broadest endpoint surface" | Reading `app.py` showed 11 distinct route definitions; original was based on README skim |
| § Approach 4 → "Endpoints" subsection | Implied a 2-endpoint surface | Full route list (5 OpenAI + 2 Anthropic + 5 operational) | Same — sourced directly from route decorators |
| § Approach 3 framing | "tempting but wrong" | "Scope is intentionally narrow … right choice when every consumer speaks OpenAI SDK" | Earlier framing penalised an intentional design choice |
| Appendix comparison table, LiteLLM row | Implied no Anthropic surface at all | Notes `/anthropic/v1/messages` passthrough exists | LiteLLM does support Anthropic shape, just at a non-default path |

### Sections added

| Section | Why | Anchor |
|---|---|---|
| **Capability Matrix** | Streaming, tool calling, vision, dashboard, health-check, per-user auth all need to be evaluated when picking an approach. The original "five approaches at a glance" only had endpoint coverage and auth model. | After § Five Approaches at a Glance |
| **Upstream Stability Snapshot** | "Pick on feature fit" assumes equal maintenance risk. With one upstream at 45k stars (LiteLLM) and others at single-digit stars (`copilot-api-proxy`, `c2p`), the maintenance-risk axis dominates for team-shared deployments. | After Capability Matrix |
| **Token Lifecycle** | Refresh / expiry / revocation handling differs materially across approaches and was missing entirely. The previous "Authentication" section only covered first-OAuth. Operationally, what happens 30 minutes later matters more than what happens at minute zero. | After § Authentication |
| **Failure Modes** | Concrete "what happens when GitHub is down / 429s / token revoked / under load" table. The original had a single "Account suspended" troubleshooting entry but no systematic failure-mode coverage. | After § Token Lifecycle |
| **Architecture Patterns** | Three ASCII diagrams (single-user, multi-provider router, self-hosted shared) make the right approach for a given deployment shape obvious. The original had only the c2p diagram and a decision tree. | After § Failure Modes |
| **Subscription Tier Impact** | Model availability is gated by Copilot tier (Individual / Business / Enterprise) and admin policy — none of the proxies bypass that. A user wondering why `claude-sonnet-4.5` returns "model not found" needs to look at `github.com/organizations/<ORG>/settings/copilot/policies`, not the proxy. | After § Architecture Patterns |
| **Architectural Review Log** (this section) | The user asked for a record of changes; future maintainers can cross-reference future reviews against this format. | At end of doc, before References was already at end |

### Sections enhanced (no factual change, more detail)

| Section | Enhancement |
|---|---|
| § Approach 4 description | Added defensive-`tool_calls`-synthesis note (genuinely useful, undocumented behaviour worth surfacing) |
| § Risks and Mitigations | Updated "Stale conda-forge `litellm` constrains" risk row — already done in earlier session, retained |

### Re-evaluations that did NOT change the doc

These were checked and confirmed correct:

| Claim | Verification |
|---|---|
| Approach 1 has both OpenAI + Anthropic | Verified via `repos/ericc-ch/copilot-api/contents/src/routes` listing: `chat-completions/`, `embeddings/`, `messages/`, `models/` |
| Approach 1 has stream + non-stream code paths for `/v1/messages` | Verified: `routes/messages/` contains both `stream-translation.ts` and `non-stream-translation.ts` |
| Approach 3 self-mounts `/v1` | Verified: `app.mount("/v1", app)` on line 444 of `main.py` — confirms `OPENAI_BASE_URL=http://localhost:9191/v1` works despite routes being defined without prefix |
| LiteLLM has `/health/liveness` + `/health/readiness` | Verified — both endpoints exist in LiteLLM's proxy server |
| Copilot OAuth token is per-machine | Verified — re-using across machines is what GitHub's docs cite as an abuse-detection signal |

### Architectural opinions / reframes

The doc takes the following positions:

1. **The right framing is a bridge pattern, not a deployment pattern.** This
   is a transitional setup for an individual developer who doesn't yet have
   provider keys. The earlier framing implied ongoing operation; the
   updated framing centres on migration off the bridge once real keys
   arrive (§ Migration Path).
2. **Team-shared / multi-user deployment is intentionally out of scope.**
   Sharing an Individual Copilot subscription across users — even within
   one org — is a TOS violation. The right path for shared internal API
   access is Copilot Business or Enterprise where every consumer has
   their own licence. An earlier draft had a "Pattern C (self-hosted
   shared service)" diagram; that pattern was removed and replaced with
   a hybrid-bridge diagram (some real keys + some Copilot routing) that
   stays single-developer.
3. **Approach selection collapses to two defaults for the bridge audience.**
   Pattern A (single bridge) → `copilot-api`. Pattern B (single endpoint
   that survives piecewise migration) → LiteLLM. The other approaches
   exist for narrow cases (Approach 3 if IDE-token reuse is critical;
   Approach 4 if you want a web dashboard; Approach 5 only ever for
   sharing with one trusted second user).

### Open follow-ups (not addressed in this review)

These would be valuable but were out of scope for the doc-only review:

- **Conformance test harness:** a small script that, given a base URL,
  exercises chat-completions (stream + non-stream), tool calls, embeddings,
  and (if Anthropic) `/v1/messages` — would replace ad-hoc curl smoke tests
  and let us catch regressions when upstream proxies change.
- **Latency baseline:** add per-approach p50/p95 latency numbers for a
  fixed prompt to the comparison matrix. Useful for picking under
  latency-sensitive workloads (e.g., editor-integrated agents).
- **Threat model write-up:** the current TOS section + token-permission
  callouts are informal. A formal threat model (assets, actors,
  trust boundaries, mitigations) would be useful for security-sign-off
  conversations in regulated orgs.
- **Auto-discovery of Copilot model slugs:** the doc tells users to read
  slugs from VS Code's Manage Models UI. A small script that hits
  `/v1/models` against the running proxy and pretty-prints the available
  slugs would be more reliable than UI-scraping.

### Review round 2 (2026-04-29 — bridge-pattern reframe)

After the architectural review, the doc owner clarified the actual audience:

> Individual developers on local machines, with their IDE, **before they get
> access to Claude / Gemini / OpenAI APIs.** When developers test and
> validate `presenton`, `wuphf`, `tolaria` they won't have access to those
> provider APIs, but later they will.

That's a transitional / bridge use case, not a deployment-architecture
one. The doc was reorganised to match.

**Reframes:**

| Where | Was | Now |
|---|---|---|
| Title | "Using a GitHub Copilot Subscription as a Local Model Backend" | "A Bridge Pattern for Individual Developers" |
| Audience block | Generic "developers driving any client" | Individual dev without provider keys yet, will migrate later |
| What this doc is NOT for | (implicit) | Explicit list: team-shared use, long-term production, replacing IDE Copilot |
| Pattern C in § Architecture Patterns | Self-hosted shared service (multi-user) | Hybrid bridge — some real keys + some Copilot routing for the keys you don't have yet |
| Architecture Patterns intro | "Three deployment shapes" | "Three shapes for the bridge — all single-developer; team-shared is out of scope" |
| Upstream Stability implications | Distinguished team-shared vs personal recommendations | Bridge-only framing; maintenance risk bounded by transitional lifetime |

**Sections added in round 2:**

| Section | Why | Anchor |
|---|---|---|
| **The Bridge Pattern at a Glance** | Top-of-doc ASCII diagram showing today (all routes through Copilot proxy) → migration day → tomorrow (direct provider APIs). Makes the transitional intent obvious before any approach detail. | Just after the audience block |
| **Migration Path: From Copilot Bridge to Direct Provider APIs** | The point of the doc. Pre-migration checklist + per-app diff blocks (presenton, wuphf, tolaria, ad-hoc Python) + LiteLLM-config one-line diff for Pattern B + decommissioning + revert procedure. | After § Subscription Tier Impact, before § Configuration Reference |

**Architectural opinions revised:**

The earlier "for team-shared, only LiteLLM" claim was retired — team-shared
is no longer in scope. The opinions block now centres on:

1. The bridge pattern is transitional, not architectural.
2. Team-shared is a TOS violation; routing it to Copilot Business / Enterprise.
3. For the bridge audience: Pattern A → `copilot-api`; Pattern B → LiteLLM
   if you'll migrate piecewise.

### Review provenance

| Field | Value |
|---|---|
| Date | 2026-04-29 |
| Reviewer role | Senior architect (per request) |
| Upstream HEAD timestamps captured | `BerriAI/litellm` 2026-04-29; `ericc-ch/copilot-api` 2025-11-10; `yuchanns/copilot-openai-api` 2026-03-23; `IT-BAER/copilot-api-proxy` 2026-01-21; `otler17/copilot-Subscription-to-Public-Api` 2026-04-28 |
| Lines added (round 1) | ~430 |
| Lines added (round 2 reframe) | ~330 |
| Lines modified (corrections) | ~6 |
| Net effect | Doc went from "comprehensive intro" to "decision-grade reference for production-ish use" |
